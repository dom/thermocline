"""SP-3.3 signature wire protocol: ``sign_envelope`` / ``verify_envelope``.

These helpers implement the normative SP-3.3 clauses from the README so every
consumer signs and verifies envelopes the same way instead of reverse-
engineering the reference coordinator:

* **SP-3.3-02 (pre-fill ordering)**: all non-``sig`` fields of the signature
  block are populated before canonicalization.
* **SP-3.3-01 (canonicalization invariant)**: the envelope is canonicalized
  with the signature block's ``sig`` set to the empty string ``""`` (NOT
  removed), both when signing and when verifying, so the signer and verifier
  agree on the map-key set.
* The signature bytes are hex-encoded into ``<block>.sig``; verification
  reverses this (hex-decode, reset ``sig`` to ``""``, verify).

The signature block is ``dispatch_signature`` for ``task`` / ``job`` envelopes
and ``receipt_signature`` for ``task_result`` / ``job_result`` envelopes. The
field vocabulary is exactly the Pydantic model field names (``key_scheme``,
``node_id``, ``channel_id``, ``timestamp``, ``sig``, ...); there is no
``bytes_hex`` alias (SP-3.3-03's tolerance clause was retired in 0.4.0 to keep
the wire single-shaped under ``extra="forbid"``).

The ``none`` key scheme is an explicit unsigned path: :func:`verify_envelope`
raises :class:`SchemeError` (code ``UNSIGNED_SCHEME_REJECTED``) unless the
caller opts in with ``allow_unsigned=True``, in which case it returns an
:class:`UnsignedAck` rather than a :class:`Receipt`.
"""
from __future__ import annotations

import copy
from typing import Any

from .envelope import Job, JobResult, Task, TaskResult
from .errors import IdentityError, SchemeError
from .identity import IdentityProvider, Receipt, Signature, UnsignedAck, Verifier
from .schemes import KeyScheme

__all__ = ["sign_envelope", "verify_envelope"]

_DISPATCH_TYPES = frozenset({"task", "job"})
_RECEIPT_TYPES = frozenset({"task_result", "job_result"})

_PARSE_BY_TYPE: dict[str, type[Task] | type[Job] | type[TaskResult] | type[JobResult]] = {
    "task": Task,
    "job": Job,
    "task_result": TaskResult,
    "job_result": JobResult,
}


def _signature_block_key(env_type: object) -> str:
    if env_type in _DISPATCH_TYPES:
        return "dispatch_signature"
    if env_type in _RECEIPT_TYPES:
        return "receipt_signature"
    raise SchemeError(
        f"cannot sign or verify envelope of type {env_type!r}: only "
        "task/job (dispatch_signature) and task_result/job_result "
        "(receipt_signature) carry a signature block",
        code="UNSUPPORTED_KEY_SCHEME",
    )


def sign_envelope(
    envelope: dict[str, Any],
    provider: IdentityProvider,
    *,
    signer_identity: str,
) -> Task | Job | TaskResult | JobResult:
    """Sign ``envelope`` per SP-3.3 and return the parsed, signed model.

    ``envelope`` is a plain dict whose signature block already carries every
    non-``sig`` field (SP-3.3-02). The block's ``node_id`` must equal
    ``signer_identity``; if absent it is filled in, if present and different an
    :class:`IdentityError` is raised (the node_id binding is authoritative).

    The returned model is re-parsed through ``parse_strict`` so the caller gets
    a validated envelope with ``<block>.sig`` populated with the hex signature.
    """
    env = copy.deepcopy(envelope)
    env_type = env.get("type")
    block_key = _signature_block_key(env_type)
    block = env.get(block_key)
    if not isinstance(block, dict):
        raise IdentityError(
            f"envelope is missing its {block_key!r} block; SP-3.3-02 requires "
            "all non-sig fields pre-filled before signing",
            code="MALFORMED_ENVELOPE",
        )

    declared_node_id = block.get("node_id")
    if declared_node_id is None:
        block["node_id"] = signer_identity
    elif declared_node_id != signer_identity:
        raise IdentityError(
            f"signature block node_id {declared_node_id!r} does not match "
            f"signer_identity {signer_identity!r}",
            code="NODE_ID_MISMATCH",
        )
    block["sig"] = ""

    # Sign over the *model-dumped* wire form, not the raw input dict: the model
    # normalizes field presence (e.g. default ``result_policy: null``) so the
    # bytes the signer covers are exactly the bytes a verifier reconstructs
    # from the parsed envelope. Signing the raw dict would omit defaulted
    # fields and the verifier's canonical bytes would then diverge.
    parse_cls = _PARSE_BY_TYPE[str(env_type)]
    wire: dict[str, Any] = parse_cls.parse_strict(env).model_dump(mode="json")

    # SP-3.3-01: canonicalize (inside provider.sign) with sig set to "".
    wire[block_key]["sig"] = ""
    signature = provider.sign(envelope=wire, signer_identity=signer_identity)
    wire[block_key]["sig"] = signature.bytes_.hex()

    return parse_cls.parse_strict(wire)


def verify_envelope(
    payload: dict[str, Any],
    verifier: Verifier,
    *,
    allow_unsigned: bool = False,
) -> Receipt | UnsignedAck | None:
    """Verify a signed envelope per SP-3.3.

    Returns a :class:`Receipt` on success, ``None`` on signature failure /
    tamper / node_id mismatch, and (only when ``allow_unsigned=True`` and the
    declared scheme is ``none``) an :class:`UnsignedAck`.

    Raises :class:`SchemeError` (code ``UNSIGNED_SCHEME_REJECTED``) when the
    envelope declares ``key_scheme=none`` and the caller did not opt into the
    unsigned path. This is the hook a forge (Seamount) uses to REQUIRE a
    signature: leave ``allow_unsigned`` at its default and ``none`` is refused.
    """
    env = copy.deepcopy(payload)
    env_type = env.get("type")
    block_key = _signature_block_key(env_type)
    block = env.get(block_key)
    if not isinstance(block, dict):
        raise SchemeError(
            f"envelope has no {block_key!r} block to verify",
            code="UNSUPPORTED_KEY_SCHEME",
        )

    scheme_value = block.get("key_scheme")
    if scheme_value == KeyScheme.NONE.value:
        envelope_id = str(
            env.get("envelope_id") or env.get("job_id") or ""
        )
        if not allow_unsigned:
            raise SchemeError(
                "envelope declares key_scheme=none (unsigned); refusing to "
                "treat it as verified. Pass allow_unsigned=True to accept the "
                "unsigned tier-0 path.",
                code="UNSIGNED_SCHEME_REJECTED",
            )
        return UnsignedAck(envelope_id=envelope_id)

    node_id = block.get("node_id")
    if not isinstance(node_id, str):
        raise SchemeError(
            f"{block_key!r} block is missing a string node_id",
            code="UNSUPPORTED_KEY_SCHEME",
        )
    sig_hex = block.get("sig")
    if not isinstance(sig_hex, str) or sig_hex == "":
        # No signature material to check: not a verified envelope.
        return None
    try:
        sig_bytes = bytes.fromhex(sig_hex)
    except ValueError:
        return None
    if not isinstance(scheme_value, str):
        raise SchemeError(
            f"{block_key!r} block is missing a string key_scheme",
            code="UNSUPPORTED_KEY_SCHEME",
        )

    # SP-3.3-01: reset sig to "" so the verify canonicalization matches the
    # signer's.
    block["sig"] = ""
    signature = Signature(
        scheme=KeyScheme(scheme_value),
        bytes_=sig_bytes,
        signer_identity=node_id,
    )
    return verifier.verify(envelope=env, signature=signature)
