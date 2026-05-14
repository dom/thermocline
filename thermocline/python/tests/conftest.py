"""Shared pytest fixtures for the thermocline-py test suite.

This file is consumed by every test file in ``tests/`` (pytest auto-discovers
``conftest.py``). It provides the ``brine_in_memory_keyring`` fixture used by
the cross-role / scheme-lookup / keystore-probe / generate-idempotent
behavioral tests.

Coexistence note:
The pre-existing module-scoped ``fake_keyring`` fixture inside
``tests/test_identity_brine_roundtrip.py`` is intentionally preserved as-is.
That fixture uses a ``MagicMock`` backend and is wired ONLY for the existing
13 brine round-trip tests. The ``brine_in_memory_keyring`` fixture below
uses a REAL ``keyring.backend.KeyringBackend`` subclass so the keystore-probe
isinstance check sees a live, non-fail/non-null class. The two fixtures are
NOT interchangeable (the MagicMock cannot satisfy isinstance checks against
real keyring backend classes); they coexist intentionally.
"""
from __future__ import annotations

from typing import Iterator

import keyring
import pytest
from keyring.backend import KeyringBackend


class _InMemoryKeyringBackend(KeyringBackend):
    """Real ``KeyringBackend`` subclass backed by a per-instance dict.

    Class name is deliberately NOT ``Keyring`` so it is unambiguously distinct
    from ``keyring.backends.fail.Keyring`` and ``keyring.backends.null.Keyring``
    (both of which the keystore-probe isinstance check rejects).
    """

    priority: float = 100  # type: ignore[assignment]

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        self._store.pop((service, username), None)


@pytest.fixture
def brine_in_memory_keyring() -> Iterator[_InMemoryKeyringBackend]:
    """Install a real in-memory ``KeyringBackend`` for the duration of one test.

    Yields the backend instance so a test may introspect ``backend._store`` if
    it needs to assert no key bytes leak elsewhere. Restores the
    previously-installed backend on teardown so test isolation is preserved.
    """
    previous = keyring.get_keyring()
    backend = _InMemoryKeyringBackend()
    keyring.set_keyring(backend)
    try:
        yield backend
    finally:
        keyring.set_keyring(previous)
