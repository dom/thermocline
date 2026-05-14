# `thermocline-py`

Reference Python library for the [Thermocline envelope spec](../README.md).

`thermocline-py` is the type-and-crypto contract layer of the Thermocline Suite.
Every other suite component — Photophore (policy engine), `pi-forge`, and
`describe-forge` — imports from this package. It deliberately ships zero network
code and zero policy logic. It establishes:

- Pydantic v2 models for every envelope shape (`task`, `task_result`, `job`,
  `job_result`, `error`).
- The `Sensitive[T]` redaction wrapper used to type any privacy-sensitive
  byte content. `repr`/`str` are redacted; `.reveal()` is the only unwrap path.
- `KeyScheme` enum, `SUPPORTED_VERSIONS`, and an `EnvelopeError` exception
  hierarchy with stable string error codes.
- `thermocline.canonical.canonicalize` — the single canonical-JSON
  signing-input path across the entire suite (RFC 8785 / JCS via `rfc8785`).
- `IdentityProvider` Protocol + `brine` reference adapter (PyNaCl
  Ed25519) that delegates every signature to the platform keystore.
- JSON Schema Draft 2020-12 artifacts under `thermocline/schema/`, generated
  from the Pydantic models with a CI drift check.

## Install

```bash
pip install -e ".[dev]"          # from the thermocline/python/ directory
```

Python 3.11+ is required. Pydantic is pinned to `>=2.7,<3.0` — v1 patterns
(`.dict()`, `.json()`) are forbidden by CI lint.

## Quickstart

```python
from thermocline import Task, ContentBlock, Sensitive, SUPPORTED_VERSIONS

assert "0.3.1" in SUPPORTED_VERSIONS

task = Task(
    thermocline="0.3.1",
    type="task",
    envelope_id="11111111-2222-4333-8444-555555555555",
    issued_at="2026-05-08T00:00:00Z",
    issuer="my-sovereign-node",
    channel_id="chan-pi-forge-local",
    task={
        "type": "data.compute",
        "instruction": "Compute pi to 100 digits.",
        "parameters": {"digits": 100},
    },
    context=[
        ContentBlock(
            tier=2,
            role="task_background",
            content=Sensitive(b"This is a reference test. No private context."),
        ),
    ],
)

# Redacted by default — bytes never appear in repr/str/log output.
print(repr(task.context[0]))      # …content=<Sensitive: bytes> …
# Wire-transparent: model_dump_json() emits base64 for the bytes.
payload = task.model_dump_json()
roundtripped = Task.model_validate_json(payload)
assert roundtripped == task
```

## Where things live

- `src/thermocline/version.py` — `SUPPORTED_VERSIONS` (`{"0.3.0", "0.3.1"}`)
  and `validate_version()`.
- `src/thermocline/errors.py` — `EnvelopeError` and typed subclasses with
  stable error codes.
- `src/thermocline/sensitive.py` — `Sensitive[T]` wrapper.
- `src/thermocline/schemes.py` — `KeyScheme` enum.
- `src/thermocline/envelope.py` — Pydantic v2 envelope models.
- `src/thermocline/scripts/build_schemas.py` — schema generator (`--write` /
  `--check`).
- `tests/` — unit + property tests (run with `pytest`).
- `../schema/` — generated JSON Schema artifacts (committed; CI checks for
  drift).

## Design references

- Spec: [`../README.md`](../README.md) (Thermocline v0.3.0-draft) — the source
  of truth for envelope shape and field semantics.
- Design discipline (load-bearing rules enforced by tests and CI):
  - `Sensitive[T]` discipline — bytes never leak via repr/str/logger.
  - `json.dumps` is forbidden in signing paths (canonical JSON only,
    enforced by `tests/test_no_json_dumps.py`).
  - Pydantic v1 patterns (`.dict()`, `.json()`) are forbidden by lint.
  - Receipt construction is gated behind a module-private sentinel so a
    `Receipt` always represents a verified envelope.

## License

MIT — see [`../LICENSE`](../LICENSE) (or fall back to repository-level license).
