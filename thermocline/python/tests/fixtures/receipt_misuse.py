"""Deliberate D-01 misuse fixture. ``mypy --strict`` on this file MUST fail.

This file is referenced by
:func:`tests.test_identity_receipt_private.test_mypy_strict_rejects_receipt_misuse`,
which runs ``mypy --strict`` against this single file in a subprocess and asserts
non-zero exit. The static gate fails because :class:`thermocline.identity.Receipt`
requires a module-private ``_token`` parameter (no default) and the only valid
type for that token (``_ReceiptConstructorToken``) is module-private to
``thermocline.identity`` — external code has nothing valid to pass.

If a future change to ``Receipt.__init__`` makes ``_token`` optional, mypy will
suddenly accept this file, the test will fail, and the build will break — which
is exactly what the test exists to guarantee (T-03-10).
"""
from datetime import datetime, timezone

from thermocline.identity import Receipt
from thermocline.schemes import KeyScheme

# The line below is the misuse: external code constructing a Receipt directly.
# mypy --strict MUST reject this because ``_token`` is required (no default) and
# the only valid value is ``_ReceiptConstructorToken``, which is module-private
# to ``thermocline.identity``.
bad: Receipt = Receipt(
    envelope_id="forged",
    signature_hash="forged",
    verified_at=datetime.now(timezone.utc),
    key_scheme=KeyScheme.BRINE,
)
