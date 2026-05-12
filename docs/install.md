# Thermocline-py Install Guide

## 1. Prerequisites

- **Python**: 3.11+ (3.12 recommended for type-narrowing improvements).
- **OS** (first-class): macOS 12+ (Apple Silicon or Intel). The `python-keyring`
  backend uses macOS Keychain Services.
- **OS** (secondary): Linux with libsecret + an active D-Bus session; Windows 10+
  with Credential Manager. Both are tested best-effort; not gated in CI.
- **Build tools**: none (pure-Python wheels for all transitive deps).

## 2. Install

Recommended (uv):

```bash
cd thermocline/thermocline/python
uv venv
uv pip install -e .[dev]
```

Alternative (pip + venv):

```bash
cd thermocline/thermocline/python
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## 3. Verify

```bash
python -c "from thermocline import canonicalize, BrineProvider; print('ok')"
```

Expected: `ok` on stdout.

Run the test suite (non-keystore tests):

```bash
pytest -m "not keystore" -q
```

Expected: 150+ passed, 3 skipped.

## 4. Keystore Prerequisites

Thermocline-py delegates all key management to `python-keyring`, which is
installed automatically. Platform-specific notes:

- **macOS**: works out of the box. First use triggers Keychain prompts —
  click "Always Allow" once per service namespace (`thermocline.brine`,
  `seamount.piforge`, `seamount.describeforge`).
- **Linux**: requires libsecret + a running D-Bus session. Headless servers
  must run a `dbus-daemon` instance or use `keyrings.cryptfile` as a
  software-only fallback (NOT recommended for production sovereign nodes).
- **Windows**: works out of the box with Credential Manager. No first-run
  prompts.

If the platform keystore is unavailable, `BrineProvider` raises
`KeystoreUnavailableError` and refuses to start (IDENT-05 / Phase 1 BL-03).

## 5. Known Limitations (v0.1)

Default `python-keyring` macOS Keychain entries are software-backed
(encrypted at rest, gated by the user's login session). Hardware-anchored
Secure Enclave entries require Apple Silicon and a developer signing identity,
and are deferred to v0.2. The v0.1 threat model is satisfied without Secure
Enclave: key material never leaves the keystore.

## Next steps

- [Quickstart](quickstart.md) — full clone-to-first-dispatch walkthrough.
- [Operations](ops.md) — library has no ops surface; cross-refs.
- [ADRs](adr/index.md) — architecture decisions.
