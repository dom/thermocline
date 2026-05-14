# ADR-0005: No in-process key material

**Status:** Accepted · 2026-05-12

## Context

The Thermocline threat model treats node identity (an ed25519 keypair) as the
single most valuable secret in the system. Compromise of a private key permits
forge impersonation (AT-E4), forged dispatch signatures (AT-C4), and channel
impersonation. The mitigation is: the private key MUST never enter the
implementing process's address space outside the brief RPC window the platform
keystore necessarily exposes.

`python-keyring` provides this property on macOS (Keychain), Linux (libsecret),
and Windows (Credential Manager). The reference brine adapter calls the keystore
for each signature operation and discards the returned bytes immediately.

## Decision

`thermocline.IdentityProvider` is a Protocol with `sign` and `verify` methods
that return `Signature` and `Receipt` value types, NOT `PrivateKey`. The brine
reference adapter holds no key material between RPCs; the adapter refuses to
start when `python-keyring` cannot reach the platform secure keystore (no
fall-back to file or env-var storage). `Receipt` is constructible only by
`IdentityProvider.verify` returning success — "skipped verification" cannot
be expressed in code (IDENT-04).

## Consequences

- ✓ Key material never crosses the process boundary except through the keystore RPC.
- ✓ Hardware-backed keystores (Apple Silicon Secure Enclave, Windows TPM) are
  drop-in upgrades — no code changes needed.
- ✓ Tests cannot "skip verification" — type system forbids it.
- ✗ Performance: each signature is a keystore RPC. For high-throughput dispatch
  this could add latency; v0.1 dispatch volume makes this acceptable.
- ✗ macOS Secure Enclave hardware-anchored entries require a developer signing
  identity; deferred to a subsequent milestone (see CHANGELOG known-limitations).

## References

- IDENT-02, IDENT-04, IDENT-05 in `thermocline/README.md`
- `thermocline/python/src/thermocline/identity.py` (`BrineProvider.__init__` keystore-required guard)
