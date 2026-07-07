"""Pydantic v2 envelope models for the Thermocline spec.

Models exactly five envelope shapes per ``../README.md``:

* :class:`Task` — request envelope with ``task`` block + ``context[]``.
* :class:`TaskResult` — response envelope with ``outputs`` + receipt signature.
* :class:`Job` — multi-step manifest-driven dispatch.
* :class:`JobResult` — terminal job result with ``status`` + optional artifact.
* :class:`ErrorEnvelope` — structured error response (pi-forge style:
  ``type: "task_error"`` with a nested ``error`` block).

All models use ``ConfigDict(extra="forbid")`` per THERMO-03 — extra fields are
rejected with a Pydantic ``ValidationError``. The version field is named
``thermocline`` on the wire (matching the spec) and validates against
:data:`thermocline.version.SUPPORTED_VERSIONS`; unknown versions raise
:class:`UnsupportedVersionError` (THERMO-07).

``ContentBlock.content`` is typed :class:`Sensitive[bytes]` (D-03) so accidental
``repr``/``logger`` calls cannot leak the underlying bytes (Pitfall 4).
"""
from __future__ import annotations

from typing import Any, Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .errors import UnsupportedVersionError
from .schemes import KeyScheme
from .sensitive import Sensitive
from .version import SUPPORTED_VERSIONS, validate_version

# ---------------------------------------------------------------------------
# Common base.


class _EnvelopeBase(BaseModel):
    """Shared model config — strict validation, no extras (THERMO-03)."""

    model_config = ConfigDict(
        extra="forbid",
        # Models are not mutated post-construction in this library; freeze them
        # to surface accidental writes as runtime errors.
        frozen=True,
        # ContentBlock.content uses the Sensitive generic.
        arbitrary_types_allowed=True,
    )


# ---------------------------------------------------------------------------
# Sub-objects shared across envelopes.


class _Shadow(BaseModel):
    """Photophore-generated shadow placed into a tier-1 ``ContentBlock``.

    Spec: ``thermocline/README.md`` § Task Envelope (`shadow` substructure).
    Photophore generates these; thermocline-py only needs to round-trip them.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    shadow_id: str
    content_type: str
    abstraction: str
    relevance: float


class ContentBlock(_EnvelopeBase):
    """A single context entry inside ``Task.context[]`` or job ``step.context[]``.

    A block carries either ``content`` (tier-2 public bytes, wrapped in
    :class:`Sensitive` so repr/log calls don't leak it) OR ``shadow`` (tier-1
    abstraction). Tier-0 (``local``) content never appears in an envelope: the
    Photophore policy engine strips it before signing.
    """

    tier: Literal[0, 1, 2]
    role: str
    content: Sensitive[bytes] | None = None
    shadow: _Shadow | None = None

    @model_validator(mode="after")
    def _enforce_tier_semantics(self) -> "ContentBlock":
        """Enforce invariant #1 of the suite: tier determines the payload shape.

        * tier 0 (``local``): must carry neither ``content`` nor ``shadow``.
          A local block never belongs in a dispatched envelope, so raw
          ``content`` (or even a ``shadow``) on a tier-0 block is a
          privacy-boundary violation, not a soft warning.
        * tier 1 (``shared``): must carry ``shadow`` and must NOT carry
          ``content`` (dispatched only as an abstraction).
        * tier 2 (``public``): must carry ``content`` and must NOT carry
          ``shadow`` (transmitted as-is).

        Prior to 0.4.0 this was documented in a comment and delegated to the
        policy engine. The envelope layer now enforces it directly so every
        consumer (and every cross-language port, via the JSON Schema
        ``if``/``then`` clauses) inherits the rule.
        """
        has_content = self.content is not None
        has_shadow = self.shadow is not None
        if self.tier == 0:
            if has_content or has_shadow:
                raise ValueError(
                    "tier-0 (local) block must not carry content or shadow in a "
                    "dispatched envelope: local content never crosses the boundary"
                )
        elif self.tier == 1:
            if not has_shadow:
                raise ValueError("tier-1 (shared) block requires a shadow")
            if has_content:
                raise ValueError(
                    "tier-1 (shared) block must not carry raw content; it is "
                    "dispatched only as a shadow"
                )
        else:  # tier == 2
            if not has_content:
                raise ValueError("tier-2 (public) block requires content")
            if has_shadow:
                raise ValueError("tier-2 (public) block must not carry a shadow")
        return self


class _TaskBlock(BaseModel):
    """Inner ``task`` block of the Task envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str
    instruction: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ResultPolicy(BaseModel):
    """``result_policy`` block — issuer-authored result handling rules.

    thermocline-py ships the model only; Photophore authors policy values.

    Public name is ``ResultPolicy``; renamed from a private ``_ResultPolicy``
    in v0.3 so Photophore and future cross-language ports can import without
    depending on a private name.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    persist_to_shared: list[str] = Field(default_factory=list)
    return_only: list[str] = Field(default_factory=list)
    strip_before_persist: list[str] = Field(default_factory=list)


# Backward-compat alias for pre-v0.3 callers that imported ``_ResultPolicy``.
# Alias remains for at least one minor cycle (v0.3.x); may be removed in v0.4.
_ResultPolicy = ResultPolicy  # noqa: E305


class _DispatchSignature(BaseModel):
    """``dispatch_signature`` block carried on signed envelopes.

    Signing happens in :mod:`thermocline.identity`; this model just
    round-trips the wire shape.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    key_scheme: KeyScheme
    node_id: str
    channel_id: str
    policy_hash: str | None = None
    shadows_generated: list[str] = Field(default_factory=list)
    timestamp: str
    sig: str | None = None


class _ReceiptSignature(BaseModel):
    """``receipt_signature`` block on a result envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key_scheme: KeyScheme
    node_id: str
    envelope_id: str | None = None
    job_id: str | None = None
    result_id: str | None = None
    inputs_received: list[str] = Field(default_factory=list)
    timestamp: str
    sig: str | None = None


class _Provenance(BaseModel):
    """``provenance`` block on result envelopes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    shadows_received: list[str] = Field(default_factory=list)
    tiers_present: list[int] = Field(default_factory=list)
    steps_executed: list[str] = Field(default_factory=list)
    local_tiers_present: bool = False


# ---------------------------------------------------------------------------
# Versioned base — adds the ``thermocline`` field validator.


class _VersionedEnvelope(_EnvelopeBase):
    """Adds the ``thermocline`` field plus a validator that rejects unknown values.

    Subclasses inherit the validator. THERMO-07.
    """

    thermocline: str

    @field_validator("thermocline")
    @classmethod
    def _check_version(cls, declared: str) -> str:
        # Pydantic v2 only wraps ValueError/AssertionError/PydanticCustomError
        # raised inside a field validator into ValidationError. We catch the
        # typed UnsupportedVersionError, surface it as a ValueError so Pydantic
        # records it cleanly, and chain the typed exception via __cause__ so
        # parse_strict() can recover and re-raise the original (THERMO-07).
        try:
            validate_version(declared)
        except UnsupportedVersionError as exc:
            raise ValueError(str(exc)) from exc
        return declared


# ---------------------------------------------------------------------------
# Envelope shapes (the public surface).


_E = TypeVar("_E", bound="_VersionedEnvelope")


def _re_raise_version_errors(cls: type[_E], payload: dict[str, Any]) -> _E:
    """Validate ``payload`` via Pydantic, surface version errors as the typed exception.

    Used by ``parse_strict`` classmethods so callers that care specifically
    about version mismatches (forge handlers, conformance tests) can match on
    :class:`UnsupportedVersionError` rather than parsing Pydantic error
    structures.
    """
    try:
        return cls.model_validate(payload)
    except ValidationError as exc:
        for err in exc.errors():
            if err.get("loc") == ("thermocline",) and err.get("type") == "value_error":
                # Pydantic wraps the original under ``ctx.error``.
                ctx = err.get("ctx") or {}
                inner = ctx.get("error") if isinstance(ctx, dict) else None
                if isinstance(inner, UnsupportedVersionError):
                    raise inner from exc
                # Walk the cause chain — Pydantic v2 records the originating
                # ValueError; our validator chains the typed exception via
                # ``raise ... from exc``.
                cause = inner.__cause__ if isinstance(inner, BaseException) else None
                if isinstance(cause, UnsupportedVersionError):
                    raise cause from exc
                # Fall back: build a fresh UnsupportedVersionError using the
                # offending value, which is in err["input"].
                raise UnsupportedVersionError(
                    f"Unsupported Thermocline version: {err.get('input')!r}"
                ) from exc
        raise


class Task(_VersionedEnvelope):
    """The ``task`` request envelope (single-shot).

    Spec: ``../README.md`` § Task Envelope.
    """

    type: Literal["task"]
    envelope_id: str
    issued_at: str
    issuer: str
    channel_id: str
    task: _TaskBlock
    context: list[ContentBlock] = Field(default_factory=list)
    result_policy: ResultPolicy | None = None
    dispatch_signature: _DispatchSignature | None = None

    @classmethod
    def parse_strict(cls, payload: dict[str, Any]) -> "Task":
        """Like ``model_validate`` but re-raises version errors as the typed exception."""
        return _re_raise_version_errors(cls, payload)


class TaskResult(_VersionedEnvelope):
    """The ``task_result`` response envelope.

    Spec: ``../README.md`` § Task Result Envelope.
    """

    type: Literal["task_result"]
    envelope_id: str
    result_id: str
    completed_at: str
    responder: str
    outputs: dict[str, Any] = Field(default_factory=dict)
    provenance: _Provenance
    receipt_signature: _ReceiptSignature | None = None

    @classmethod
    def parse_strict(cls, payload: dict[str, Any]) -> "TaskResult":
        return _re_raise_version_errors(cls, payload)


class _JobOutputContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str  # "image" | "audio" | "video" | "text" | "composite"
    format: str
    destination: str  # "local" | "return" | "<path>"


class _JobConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    may_access: list[str] = Field(default_factory=list)
    may_not_access: list[str] = Field(default_factory=list)
    privacy_fence: str | None = None


class _Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    intent: str
    output_contract: _JobOutputContract
    constraints: _JobConstraints
    result_policy: ResultPolicy
    timeout_seconds: int


class _StepInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str  # "manifest" | "step:<id>"
    field: str


class _Step(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str
    label: str
    tool: str
    model: str | None = None
    input: _StepInput
    context: list[ContentBlock] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    passthrough: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


class Job(_VersionedEnvelope):
    """The ``job`` multi-step manifest envelope.

    Spec: ``../README.md`` § Job Envelope. v0.1 ships the type only; full
    job-handling logic is v0.2 (see PROJECT.md "Out of Scope").
    """

    type: Literal["job"]
    job_id: str
    issued_at: str
    issuer: str
    channel_id: str
    manifest: _Manifest
    steps: list[_Step]
    dispatch_signature: _DispatchSignature | None = None

    @classmethod
    def parse_strict(cls, payload: dict[str, Any]) -> "Job":
        return _re_raise_version_errors(cls, payload)


class _JobArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str
    format: str
    data: str  # base64 | local_path | stream_ref — wire shape only


class JobResult(_VersionedEnvelope):
    """The ``job_result`` envelope.

    Spec: ``../README.md`` § Job Result Envelope.
    """

    type: Literal["job_result"]
    job_id: str
    result_id: str
    status: Literal["complete", "failed", "halted"]
    completed_at: str
    responder: str
    halt_reason: str | None = None
    artifact: _JobArtifact | None = None
    provenance: _Provenance
    receipt_signature: _ReceiptSignature | None = None

    @classmethod
    def parse_strict(cls, payload: dict[str, Any]) -> "JobResult":
        return _re_raise_version_errors(cls, payload)


class _ErrorBody(BaseModel):
    """Inner ``error`` block of an error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str


class ErrorEnvelope(_VersionedEnvelope):
    """Structured error response.

    Mirrors pi-forge's ``task_error`` envelope (the spec README does not yet
    formalize one — THERMO-01 carry-over candidate). Future minors may
    extend with ``references`` if the spec adds them.
    """

    type: Literal["task_error", "job_error"] = "task_error"
    envelope_id: str | None = None
    job_id: str | None = None
    error: _ErrorBody

    @classmethod
    def parse_strict(cls, payload: dict[str, Any]) -> "ErrorEnvelope":
        return _re_raise_version_errors(cls, payload)


__all__ = [
    "ContentBlock",
    "ErrorEnvelope",
    "Job",
    "JobResult",
    # Public since v0.3. Backward-compat alias _ResultPolicy retained.
    "ResultPolicy",
    "Task",
    "TaskResult",
    # The exception is part of the envelope module's public contract because
    # parse_strict raises it directly. Re-exported by the package __init__.
    "UnsupportedVersionError",
    # Sub-types are intentionally NOT exported — they're documented as
    # internal model components; downstream callers go through the top-level
    # envelope shapes.
    "SUPPORTED_VERSIONS",
]

# Re-export so callers can `from thermocline.envelope import SUPPORTED_VERSIONS`.
_ = SUPPORTED_VERSIONS
