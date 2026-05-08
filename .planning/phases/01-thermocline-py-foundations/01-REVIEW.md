---
status: issues_found
phase: 01-thermocline-py-foundations
depth: standard
files_reviewed: 38
reviewed: 2026-05-08
findings:
  blocker: 4
  warning: 12
  info: 0
  total: 16
---

# Phase 1: Code Review Report

**Reviewed:** 2026-05-08
**Depth:** standard
**Files Reviewed:** 38
**Status:** issues_found

## Summary

Reviewed `thermocline-py` v0.3.1 — Pydantic v2 envelope models, RFC 8785 canonical JSON, IdentityProvider Protocol with brine reference adapter, JSON Schema artifacts, and the Phase 1 conformance corpus.

The library is generally well-structured and the testing discipline is high. Specific privacy primitives (`Sensitive[T]` redaction, the Receipt sentinel mechanism, the `json.dumps` AST lint, schema drift check) are nicely engineered. However, **two BLOCKER defects** put the security model at serious risk:

1. `BrineProvider.public_key()` derives the public key from the **private seed** read out of the keystore — there is no separate public-key store. A verifier therefore needs the signer's private seed to verify any signature, which directly contradicts the spec's "the public key is the node identity — share it freely" guarantee (Identity Provider Interface §Constraints) and the entire role-separation premise.
2. `Verifier.verify()` reads `envelope.get("key_scheme")` from the **top level** of the envelope dict, but every real Thermocline envelope nests `key_scheme` under `dispatch_signature`/`receipt_signature`. The mismatch check therefore raises `SchemeError("declared key scheme None does not match...")` on every well-formed signed envelope. The dispatch tests pass only because they pass synthetic flat dicts (e.g., `{"key_scheme": "brine"}`) that are not real envelopes.

Additional CRITICAL issues: the `BrineProvider.__init__` keystore probe relies on substring matching against `type(backend).__name__`, but the actual production `keyring.backends.fail.Keyring` and `keyring.backends.null.Keyring` classes are both named `"Keyring"` — so the production fail/null backends are NOT detected and IDENT-05 silently fails open in production.

Total: 4 BLOCKERs, 12 WARNINGs.

---

## BLOCKER findings

### BL-01: `BrineProvider.verify` requires the signer's private seed in the verifier's keystore

- **File:** `thermocline/python/src/thermocline/identity.py:312-327, 354-402`
- **Issue:** `BrineProvider.public_key(identity=...)` reads a hex-encoded **seed (private key)** from `keyring.get_password(self._keyring_service, identity)` and derives the verify key from it via `SigningKey(...).verify_key`. `BrineProvider.verify` then calls `self.public_key(identity=signature.signer_identity)` to obtain the verify key for verification.

  This means a verifier (e.g., a forge verifying a sovereign-node-issued envelope) cannot verify any signature unless the verifier's own keyring contains the **signer's private seed**. This directly violates the spec's Identity Provider Interface §Constraints: *"The public key is the node identity — share it freely. The private key MUST never leave the secure keystore"*, and breaks the entire role-separation premise of the architecture (a forge can never legitimately hold the sovereign node's seed).

  The code path also raises `IdentityError(IDENTITY_NOT_FOUND)` from `public_key()` on lookup failure, which is wrong: a verifier missing a public key for a known signer is a different surface than a signer missing its own private key.

  The only reason any existing test passes is that the brine round-trip fixtures use a single in-memory keystore for both the signer and verifier roles.
- **Fix:** Introduce a separate public-key store (or a separate keyring service / record-type prefix) and persist the verify key explicitly on `generate()`. Then change `public_key` to read from the public store, and `verify` to look up the public key (never the seed):

  ```python
  _PUBKEY_PREFIX = "pubkey:"

  def generate(self, *, identity: str) -> None:
      sk = nacl.signing.SigningKey.generate()
      keyring.set_password(self._keyring_service, identity, sk.encode().hex())
      keyring.set_password(
          self._keyring_service, _PUBKEY_PREFIX + identity,
          bytes(sk.verify_key).hex(),
      )

  def public_key(self, *, identity: str) -> bytes:
      pk_hex = keyring.get_password(self._keyring_service, _PUBKEY_PREFIX + identity)
      if pk_hex is None:
          raise IdentityError(f"no brine public key for {identity!r}", code="IDENTITY_NOT_FOUND")
      return bytes.fromhex(pk_hex)

  def register_public_key(self, *, identity: str, verify_key: bytes) -> None:
      """Store a foreign node's public key for verification — no private seed required."""
      keyring.set_password(self._keyring_service, _PUBKEY_PREFIX + identity, verify_key.hex())
  ```

  Add a behavioral test: a `BrineProvider` with only the public key registered (no seed) verifies a signature successfully.

### BL-02: `Verifier.verify` reads `key_scheme` from the wrong location for real envelopes

- **File:** `thermocline/python/src/thermocline/identity.py:209-234`
- **Issue:** `declared = envelope.get("key_scheme")` looks for `key_scheme` at the **top level** of the envelope dict. But every real envelope shape (`Task`, `TaskResult`, `Job`, `JobResult`) carries `key_scheme` nested under `dispatch_signature.key_scheme` or `receipt_signature.key_scheme`. Confirmed by inspecting `envelope.py` lines 107-122 and the conformance fixture `task-pi-100-digits.json`.

  Therefore: passing any real signed envelope to `Verifier.verify(envelope=..., signature=...)` makes `declared = None`, the comparison `None != "brine"` is True, and `SchemeError("declared key scheme None does not match signature scheme 'brine'")` is raised — for legitimate signatures.

  This bug is not caught by `test_verifier_dispatches_to_correct_provider_by_scheme` (test_identity_dispatch.py:65), `test_verifier_rejects_envelope_signature_scheme_mismatch` (line 84), or `test_verifier_dispatch_round_trips_brine_signature` (test_identity_brine_roundtrip.py:233) because every one of them passes a hand-crafted flat dict like `{"envelope_id": "...", "key_scheme": "brine"}` rather than a real envelope. The conformance fixture AT-C4 (which is *intended* to exercise this surface) similarly has `dispatch_signature.key_scheme = "brine"` with no top-level `key_scheme`; the harness only checks JSON parseability for AT-C4, not actual rejection through `Verifier.verify`.
- **Fix:** Either (a) change Verifier to read from the documented nested location:

  ```python
  def _extract_declared_scheme(self, envelope: dict[str, Any]) -> str | None:
      for key in ("dispatch_signature", "receipt_signature"):
          block = envelope.get(key)
          if isinstance(block, dict) and "key_scheme" in block:
              return block["key_scheme"]
      return envelope.get("key_scheme")  # tolerate flat for stub callers
  ```

  Or (b) accept a typed `Task | TaskResult | Job | JobResult | dict` and consult the appropriate field. Then add a regression test that runs a real `Task` envelope with `dispatch_signature.key_scheme = "brine"` through `Verifier.verify` and asserts a Receipt is returned.

### BL-03: `BrineProvider.__init__` keystore probe does NOT detect production fail/null backends

- **File:** `thermocline/python/src/thermocline/identity.py:273-294`
- **Issue:** The startup probe checks `if "fail" in backend_name.lower() or "null" in backend_name.lower()`, where `backend_name = type(backend).__name__`. The intent (per IDENT-05, the spec mandate, and CLAUDE.md) is to refuse any insecure fallback.

  But the actual production classes from `python-keyring` are:
  - `keyring.backends.fail.Keyring` — `__name__` is `"Keyring"`
  - `keyring.backends.null.Keyring` — `__name__` is `"Keyring"`

  Neither contains `"fail"` nor `"null"`. The substring check therefore PASSES for both production fail-mode backends, and `BrineProvider.__init__` proceeds — silently falling open in exactly the deployment scenarios the spec mandates be rejected (e.g., a Linux server with no D-Bus session, where keyring auto-selects the null backend).

  The unit tests in `test_identity_keystore_required.py:55-87` only exercise this with hand-rolled classes named `FailKeyring` / `NullKeyring`, which DO contain those substrings — so the test coverage gives a false sense of security.
- **Fix:** Replace the substring heuristic with module-path identity checks:

  ```python
  from keyring.backends import fail as _fail_backend, null as _null_backend
  ...
  if isinstance(backend, (_fail_backend.Keyring, _null_backend.Keyring)):
      raise KeystoreUnavailableError(
          f"refusing to start: keyring resolved to fail/null backend "
          f"({type(backend).__module__}.{type(backend).__name__}). "
          "Brine adapter NEVER falls back (IDENT-05).",
          code="KEYSTORE_UNAVAILABLE",
      )
  qualname = f"{type(backend).__module__}.{type(backend).__name__}"
  if "fail" in qualname.lower() or "null" in qualname.lower():
      raise KeystoreUnavailableError(...)
  ```

  Update `test_brine_refuses_to_start_with_fail_backend` and `…null_backend` to import the real `keyring.backends.fail.Keyring` / `keyring.backends.null.Keyring` and assert the adapter rejects them.

### BL-04: `BrineProvider.generate` silently overwrites an existing seed, destroying access to previously-signed envelopes

- **File:** `thermocline/python/src/thermocline/identity.py:297-310`
- **Issue:** `generate(identity=...)` calls `keyring.set_password(...)` unconditionally. If a key already exists for that identity, it is overwritten with no warning. Since the signing seed is the only material that can re-derive the verify key, overwriting it makes every previously-signed envelope unverifiable by this node. Per the spec §Identity Provider Interface, key rotation is supposed to be a deliberate, audited event (`key.rotate` is a separate capability that "archives the old one"); accidental clobber from a re-run of `generate()` violates that contract.

  This is a data-loss / availability risk: a rerun of any setup script that calls `provider.generate(identity="...")` permanently loses the prior signing identity.
- **Fix:** Guard against pre-existing keys:

  ```python
  def generate(self, *, identity: str) -> None:
      if keyring.get_password(self._keyring_service, identity) is not None:
          raise IdentityError(
              f"brine key already exists for identity {identity!r}; use rotate() to replace",
              code="IDENTITY_ALREADY_EXISTS",
          )
      sk = nacl.signing.SigningKey.generate()
      keyring.set_password(self._keyring_service, identity, sk.encode().hex())
  ```

  Document `rotate()` as the explicit replacement path and ship it (or stub it) so users have an obvious correct API.

---

## WARNING findings

### WR-01: Receipt sentinel mechanism is bypassable from any code in the same package

- **File:** `thermocline/python/src/thermocline/identity.py:92-150`
- **Issue:** D-01's claim is "Receipt is constructible only by `IdentityProvider.verify` returning success". The mechanism is a module-private sentinel `_RECEIPT_TOKEN`. Python has no enforcement of underscore-prefixed names — any code that does `from thermocline.identity import _RECEIPT_TOKEN` (which `test_identity_dispatch.py:135` does) can forge Receipts. mypy `--strict` does not block this either; underscore-prefixed names are accessible package-internally.

  The runtime gate (TypeError on bad sentinel) is fine. The static gate is real for **external** callers (the misuse fixture demonstrates that). But the docstring claim "Direct construction is forbidden by design" overstates what the mechanism enforces. This matters because the security narrative leans on it.
- **Fix:** Either (a) tighten the docstring to say "constructible only by code within `thermocline.identity`" rather than only by `verify()`, or (b) use a callable factory closure that does not expose the sentinel as a module attribute.

### WR-02: `ContentBlock` does not enforce the tier/content/shadow privacy invariant

- **File:** `thermocline/python/src/thermocline/envelope.py:69-81`
- **Issue:** A `ContentBlock` accepts: `tier=0` (per spec, tier-0 content MUST never appear in an envelope), both `content` and `shadow` simultaneously, neither, `content` set on a `tier=1` block (should be `shadow` only), `shadow` set on a `tier=2` block (should be `content` only).

  The whole privacy-tier value proposition rests on this invariant. Defense-in-depth requires the type system to encode it.
- **Fix:** Add a `model_validator(mode="after")` that enforces the invariant; add tests covering each rejection path.

### WR-03: `Verifier` API mismatch — the documented input is incompatible with the documented envelope shape

- **File:** `thermocline/python/src/thermocline/identity.py:209-234`
- **Issue:** `Verifier.verify` is typed `envelope: dict[str, Any]` but expects a flat dict whose top-level key is `key_scheme` (see BL-02). Real envelopes are nested. Every Phase 2/3 caller will trip on this.
- **Fix:** Tied to BL-02 fix.

### WR-04: `BrineProvider.sign` does not strip `dispatch_signature.sig` before canonicalization

- **File:** `thermocline/python/src/thermocline/identity.py:329-352`
- **Issue:** The canonical-JSON signing-input contract is ambiguous in this codebase: should the signer sign over the envelope **without** the signature block or **with** `sig: null`? Right now, the signer signs over whatever is in the dict. There is no helper that strips the signature block, no documentation, and no test asserting the contract.
- **Fix:** Document the contract; provide and require a `_canonical_signing_input` helper for both sign and verify; add a sign→attach→verify round-trip test.

### WR-05: `del signing_key` advertised as protection but is provably ineffective

- **File:** `thermocline/python/src/thermocline/identity.py:310, 326, 347`
- **Issue:** PyNaCl's `SigningKey` does not zero memory on `__del__`. Reviewers may misinterpret `del` as a security control.
- **Fix:** Remove the `del` calls or add a single block-comment clarifying that they are intent markers only and memory hygiene is delegated to the OS-level keystore.

### WR-06: `Sensitive[bytes].__hash__` mixes the inner bytes into the hash

- **File:** `thermocline/python/src/thermocline/sensitive.py:71-73`
- **Issue:** Hashing private bytes is a long-known anti-pattern for secret-bearing wrappers. For envelope content this is unlikely to matter, but the wrapper claims to be a privacy primitive.
- **Fix:** Make `Sensitive` un-hashable by default (`__hash__ = None`) and add a separate `.hash_for_dedup()` method, or hash on `id(self)`.

### WR-07: `Sensitive.__eq__` uses non-constant-time `==` on inner bytes

- **File:** `thermocline/python/src/thermocline/sensitive.py:65-69`
- **Issue:** Equality on `bytes` is short-circuit, not constant-time. If `Sensitive[bytes]` is ever used to wrap secrets compared against attacker-supplied input, this leaks via timing.
- **Fix:** Use `hmac.compare_digest` for bytes comparisons.

### WR-08: JSON Schema `thermocline` field is not constrained to known versions

- **File:** `thermocline/schema/{task,task_result,job,job_result,error}.schema.json`
- **Issue:** A third-party validator using only the schema would accept e.g. `"thermocline": "9.9.9"` as valid. AT-C5 conformance fixture would not be rejected by jsonschema validation alone.
- **Fix:** Either add `enum: ["0.3.0", "0.3.1"]` (handle in `build_schemas.py`), or document that the schema is a pure structural contract and version validation is a separate layer; update AT-C5 test to assert rejection at both layers.

### WR-09: `_re_raise_version_errors` fallback path swallows error information

- **File:** `thermocline/python/src/thermocline/envelope.py:184-213`
- **Issue:** Lines 208-212 build a fresh generic `UnsupportedVersionError` if the cause chain doesn't surface the typed exception; message format differs from `validate_version()`'s emit, breaking string-match callers.
- **Fix:** Use `PydanticCustomError` in the validator and translate that custom error type explicitly, eliminating the cause-chain walk.

### WR-10: `test_canonicalize_envelope_regression_pin` is named "regression-pin" but only does substring asserts

- **File:** `thermocline/python/tests/test_canonical.py:156-174`
- **Issue:** The test asserts substrings, not the full canonical bytes. Any change in field ordering, key set, default emission could shift bytes without tripping the test.
- **Fix:** Pin the full expected bytes once and compare exactly.

### WR-11: `_re_raise_version_errors` only re-raises the FIRST version error

- **File:** `thermocline/python/src/thermocline/envelope.py:192-213`
- **Issue:** When a payload has both an invalid version AND extra fields, callers see only `UnsupportedVersionError` and may miss other defects when fixing the envelope.
- **Fix:** Aggregate all errors, or document that the typed error is opportunistic.

### WR-12: `BrineProvider.public_key` raises in `verify`, leaking signer identity through error type

- **File:** `thermocline/python/src/thermocline/identity.py:312-323` (called from line 385)
- **Issue:** When a verifier tries to verify a signature for an unknown signer, `verify()` raises `IdentityError(...IDENTITY_NOT_FOUND)`. An unknown signer should look identical to a bad signature: both return `None`.
- **Fix:** In `BrineProvider.verify`, swallow `IdentityError(IDENTITY_NOT_FOUND)` from the public-key lookup and return `None`.

---

## Reviewer Note on Conformance Fixtures

AT-C1 and AT-C3 fixture documents are intentionally non-Task-shaped (AT-C1 has an `envelope_pair` wrapper; AT-C3 has the leading `_at_c_surface` and `_description` fields). This is fine because the manifest tags them `phase: 2` and Phase 1 only verifies JSON parseability. AT-C2 / AT-C4 carry similar leading underscore fields and would fail strict Task parsing too — the harness correctly skips strict parsing for them. The valid fixture pair (`task-pi-100-digits.json` / `task-result-pi-100-digits.json`) parses cleanly through Pydantic and JSON Schema; conformance MANIFEST references resolve.

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

## Summary count

- **BLOCKER:** 4 (BL-01 through BL-04)
- **WARNING:** 12 (WR-01 through WR-12)
- **Total:** 16

The two highest-priority items to address before this code ships are **BL-01** (verifier requires private key — breaks suite role separation) and **BL-02** (Verifier looks at wrong dict path — silently rejects all real envelopes). **BL-03** (production fail/null backends not detected — IDENT-05 fails open) is closely tied to the spec-mandated keystore guarantee. **BL-04** (silent key clobber) is a data-loss risk that affects users running setup scripts more than once.
