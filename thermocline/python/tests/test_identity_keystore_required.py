"""IDENT-05: Brine adapter refuses to start without a working secure keystore.

The fail/null-backend tests use the REAL production classes
(``keyring.backends.fail.Keyring`` and ``keyring.backends.null.Keyring``)
rather than hand-rolled synthetic look-alikes. Both production classes are
named ``Keyring`` -- a substring heuristic on ``type(backend).__name__``
misses both. Direct ``isinstance`` identity is the only correct probe.

The brine adapter MUST refuse to start when the platform secure keystore is
unavailable; it MUST NOT fall back to file-based or env-var-based key
storage. There is no fallback path -- the discipline is enforced both:

* Behaviorally: ``BrineProvider.__init__`` probes the keystore via
  :func:`isinstance` against ``(fail.Keyring, null.Keyring)`` and raises
  :class:`KeystoreUnavailableError` if either matches.
* Statically: the source of ``thermocline.identity`` contains zero references
  to ``os.environ``, ``os.getenv``, ``open(``, ``Path(``, or ``pathlib`` --
  if a future change introduces filesystem fallback, this test fires.
"""
from __future__ import annotations

import inspect
from typing import Any

import keyring
import pytest
from keyring.backends import fail, null


def test_brine_refuses_to_start_when_no_keyring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """IDENT-05: ``NoKeyringError`` at startup surfaces as KeystoreUnavailableError."""
    from keyring.errors import NoKeyringError

    from thermocline.errors import KeystoreUnavailableError
    from thermocline.identity import BrineProvider

    def raise_nokeyring() -> Any:
        raise NoKeyringError("no keyring backend")

    monkeypatch.setattr("thermocline.identity.keyring.get_keyring", raise_nokeyring)

    with pytest.raises(KeystoreUnavailableError) as excinfo:
        BrineProvider(keyring_service="thermocline.test.no-keystore")
    assert excinfo.value.code == "KEYSTORE_UNAVAILABLE"


def test_brine_refuses_to_start_with_fail_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production keyring.backends.fail.Keyring is named 'Keyring' (not
    'FailKeyring'). A substring heuristic would miss it; the ``isinstance``
    probe against the real class catches it.
    """
    from thermocline.errors import KeystoreUnavailableError
    from thermocline.identity import BrineProvider

    monkeypatch.setattr(keyring, "get_keyring", lambda: fail.Keyring())

    with pytest.raises(KeystoreUnavailableError) as excinfo:
        BrineProvider(keyring_service="thermocline.test.fail-backend")
    assert excinfo.value.code == "KEYSTORE_UNAVAILABLE"
    # Smoke-test the qualified-name change in the error message.
    msg = str(excinfo.value).lower()
    assert "fail" in msg or "null" in msg


def test_brine_refuses_to_start_with_null_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production keyring.backends.null.Keyring is named 'Keyring' (not
    'NullKeyring') -- caught by the ``isinstance`` probe.
    """
    from thermocline.errors import KeystoreUnavailableError
    from thermocline.identity import BrineProvider

    monkeypatch.setattr(keyring, "get_keyring", lambda: null.Keyring())

    with pytest.raises(KeystoreUnavailableError) as excinfo:
        BrineProvider(keyring_service="thermocline.test.null-backend")
    assert excinfo.value.code == "KEYSTORE_UNAVAILABLE"


def test_brine_accepts_in_memory_backend_that_is_not_fail_or_null(
    brine_in_memory_keyring,
) -> None:
    """Defense against over-rejection: a working backend (the conftest
    ``_InMemoryKeyringBackend``) that is NOT ``keyring.backends.fail.Keyring``
    or ``keyring.backends.null.Keyring`` MUST be accepted by the
    ``isinstance`` probe. The brine_in_memory_keyring fixture installs an
    in-memory backend; constructing BrineProvider here must succeed.
    """
    from thermocline.identity import BrineProvider

    p = BrineProvider(keyring_service="thermocline.test")
    p.generate(identity="alice")
    assert p.public_key(identity="alice") is not None


def test_brine_provider_source_has_no_filesystem_fallback() -> None:
    """Static lint: ``thermocline.identity`` source MUST NOT reference filesystem/env-var APIs.

    IDENT-05 forbids any fallback path. If a future change introduces
    ``os.environ`` / ``open(`` / ``pathlib`` for storing or reading key
    material, this test fires.
    """
    from thermocline import identity as identity_module

    src = inspect.getsource(identity_module)

    # Strip whole-line comments and docstring lines crudely. Keeping it crude
    # is intentional -- we want false positives to read the test and document
    # the exception explicitly rather than ducking the check.
    code_only_lines = [
        line
        for line in src.splitlines()
        if not line.lstrip().startswith("#") and '"""' not in line
    ]
    code_only = "\n".join(code_only_lines)

    forbidden = ("os.environ", "os.getenv", "open(", "Path(", "pathlib")
    for token in forbidden:
        assert token not in code_only, (
            f"thermocline.identity source contains {token!r} -- IDENT-05 forbids any "
            f"filesystem / env-var key-storage fallback. Either remove the reference, "
            f"or document an exception in the test."
        )


def test_brine_provider_imports_keyring_only_in_identity_module() -> None:
    """Architecture invariant: ``import keyring`` lives ONLY in ``thermocline.identity``.

    Mirrors the plan's acceptance criterion ``grep -rE 'import (keyring|nacl)'
    thermocline/python/src/thermocline/ | grep -v identity.py | wc -l == 0``.
    """
    from pathlib import Path as _Path

    src_root = _Path(__import__("thermocline").__file__).parent
    offenders: list[tuple[str, int, str]] = []
    for py_file in src_root.rglob("*.py"):
        if py_file.name == "identity.py":
            continue
        for lineno, line in enumerate(py_file.read_text().splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith(("import keyring", "from keyring", "import nacl", "from nacl")):
                offenders.append((str(py_file), lineno, line))

    assert offenders == [], (
        f"keyring/nacl imports must live ONLY in thermocline.identity; "
        f"found offenders: {offenders}"
    )
