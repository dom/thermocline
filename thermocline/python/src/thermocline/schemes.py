"""Key-scheme enumeration for envelope dispatch signatures.

Only :attr:`KeyScheme.BRINE` ships a working identity adapter in v0.1; the other
members are declared so the verifier-dispatch path (Plan 03 / IDENT-03) exists
and so future schemes can be added without changing the type system.
"""
from __future__ import annotations

from enum import StrEnum


class KeyScheme(StrEnum):
    """Signing scheme declared by a channel and carried in every signature block.

    Per Thermocline Design Constraint 8: key scheme is declared, never inferred.
    Verifiers MUST reject missing or unrecognized schemes; a channel's scheme is
    set at creation time and cannot change mid-session.
    """

    #: Ed25519 via PyNaCl + platform keystore — the v0.1 reference adapter.
    BRINE = "brine"

    #: PGP scheme — declared for future implementations; no v0.1 adapter.
    PGP = "pgp"

    #: X.509 / PKI scheme — declared for future implementations; no v0.1 adapter.
    X509 = "x509"

    #: No signing — used only by tier-2-only forges in conformance fixtures.
    #: Production channels MUST NOT use ``none`` — there is no integrity guarantee.
    NONE = "none"


__all__ = ["KeyScheme"]
