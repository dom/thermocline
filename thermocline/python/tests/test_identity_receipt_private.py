"""Receipt-private-constructor tests — runtime AND static gates.

Two gates:

1. **Runtime gate** — direct construction (`Receipt(envelope_id=..., ...)` without
   the module-private sentinel) raises ``TypeError``. Production code that tries
   to forge a Receipt fails immediately.

2. **Static gate** — ``mypy --strict`` rejects direct construction at type-check
   time because the ``_token`` parameter has no default and the only valid type
   for it (``_ReceiptConstructorToken``) is module-private to
   ``thermocline.identity``. The fixture file ``tests/fixtures/receipt_misuse.py``
   exists solely to be type-checked in a subprocess; that subprocess MUST exit
   non-zero.

The static gate is the more important of the two — it catches forgery attempts
during normal development, before the code ever runs. The runtime gate is the
belt-and-suspenders defense for the case where someone's editor / IDE / CI did
not run mypy.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone

import pytest

from thermocline.identity import Receipt
from thermocline.schemes import KeyScheme

# ---------------------------------------------------------------------------
# Runtime gate.


def test_receipt_direct_construction_raises_at_runtime() -> None:
    """Direct ``Receipt(envelope_id=..., ...)`` MUST raise TypeError.

    The Receipt's ``__init__`` requires a module-private sentinel ``_token``
    parameter. A foreign caller cannot pass a valid token because the sentinel
    class is module-private and not in the public namespace; the only path to
    a Receipt is through ``IdentityProvider.verify`` returning success.
    """
    with pytest.raises(TypeError):
        Receipt(  # type: ignore[call-arg]
            envelope_id="forged",
            signature_hash="forged",
            verified_at=datetime.now(timezone.utc),
            key_scheme=KeyScheme.BRINE,
        )


def test_receipt_runtime_error_mentions_design_rationale() -> None:
    """Foreign-token TypeError message names the verify-only path so devs find the rationale fast."""
    class _Foreign:
        pass

    try:
        Receipt(  # type: ignore[call-arg, arg-type]
            envelope_id="forged",
            signature_hash="forged",
            verified_at=datetime.now(timezone.utc),
            key_scheme=KeyScheme.BRINE,
            verified_identity="forged",
            _token=_Foreign(),  # type: ignore[arg-type]
        )
    except TypeError as exc:
        text = str(exc)
        assert "verify" in text.lower(), (
            "Receipt TypeError should explain that only IdentityProvider.verify produces a Receipt"
        )
    else:
        raise AssertionError("foreign-token Receipt construction should have raised TypeError")
def test_receipt_with_foreign_sentinel_object_still_rejects() -> None:
    """Even a same-named object from outside is rejected — identity check, not name."""

    class FakeToken:
        pass

    with pytest.raises(TypeError):
        Receipt(  # type: ignore[call-arg]
            envelope_id="forged",
            signature_hash="forged",
            verified_at=datetime.now(timezone.utc),
            key_scheme=KeyScheme.BRINE,
            _token=FakeToken(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Static gate.


def test_mypy_strict_rejects_receipt_misuse() -> None:
    """Run ``mypy --strict`` on tests/fixtures/receipt_misuse.py — MUST exit non-zero.

    This is the linchpin static gate. If a future change weakens
    ``Receipt.__init__`` (e.g., gives ``_token`` a default), mypy will accept the
    fixture, this test will fail, and the build will break — exactly the signal
    we want.
    """
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    fixture = os.path.join(tests_dir, "fixtures", "receipt_misuse.py")
    assert os.path.isfile(fixture), f"fixture missing: {fixture}"

    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", fixture],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, (
        "mypy --strict accepted Receipt misuse — the private-constructor "
        "static check is broken.\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    combined = result.stdout + result.stderr
    # The error must reference either the missing _token or a no-overload-matches
    # / Missing-positional-argument message — any of these is the right failure.
    assert (
        "_token" in combined
        or "Missing" in combined
        or "Argument" in combined
        or "no overload" in combined.lower()
    ), (
        f"mypy failed but the error doesn't mention _token / missing argument:\n{combined}"
    )
