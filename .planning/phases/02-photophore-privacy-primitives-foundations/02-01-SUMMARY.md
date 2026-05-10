---
phase: "02"
plan: "01"
subsystem: "photophore"
tags: ["audit-log", "channels", "cli", "blake3", "keyring", "sqlite", "conformance"]
dependency_graph:
  requires:
    - "01-05: thermocline-py public API (canonicalize, KeystoreUnavailableError, Receipt)"
  provides:
    - "AuditLog with AUDIT-01..08 coverage"
    - "ChannelStore with CHAN-01..06 coverage"
    - "photophore audit|channel CLI (CLI-01, CLI-02)"
    - "AT-A1/AT-A4/AT-A5 conformance fixtures"
  affects:
    - "02-02: classifier imports photophore.core.Tier"
    - "02-03: shadow/policy import photophore.audit.AuditLog"
    - "Phase 3: dispatch coordinator imports from photophore.{audit,channels}"
tech_stack:
  added:
    - "blake3==1.0.8 (BLAKE3 chain hash)"
    - "keyring==25.7.0 (platform trust store)"
    - "click==8.3.1 (CLI framework)"
    - "pyyaml==6.0.3 (rules config, Plan 02-02)"
    - "pathspec==1.1.1 (glob matching, Plan 02-02)"
  patterns:
    - "BL-03 isinstance probe for keystore backend (Phase 1 carry-forward)"
    - "D-07 three-step write ordering (keystore+index → audit → channels.db)"
    - "D-03 hash domain: blake3(canonicalize(entry minus entry_hash))"
    - "Hypothesis flatmap strategy for correlated integer inputs"
key_files:
  created:
    - "photophore/python/pyproject.toml"
    - "photophore/python/src/photophore/core.py"
    - "photophore/python/src/photophore/errors.py"
    - "photophore/python/src/photophore/audit/_schema.py"
    - "photophore/python/src/photophore/audit/_chain.py"
    - "photophore/python/src/photophore/audit/_types.py"
    - "photophore/python/src/photophore/audit/_store.py"
    - "photophore/python/src/photophore/audit/_anchor.py"
    - "photophore/python/src/photophore/channels/_keystore.py"
    - "photophore/python/src/photophore/channels/_index.py"
    - "photophore/python/src/photophore/channels/_types.py"
    - "photophore/python/src/photophore/channels/_store.py"
    - "photophore/python/src/photophore/channels/_bootstrap.py"
    - "photophore/python/src/photophore/cli/_errors.py"
    - "photophore/python/src/photophore/cli/_format.py"
    - "photophore/python/src/photophore/cli/audit_cmds.py"
    - "photophore/python/src/photophore/cli/channel_cmds.py"
    - "thermocline/conformance/invalid/AT-A1-channel-impersonation.json"
    - "thermocline/conformance/invalid/AT-A4-audit-log-tampering.json"
    - "thermocline/conformance/invalid/AT-A5-trust-store-colocation.json"
  modified:
    - "thermocline/conformance/invalid/MANIFEST.yaml"
decisions:
  - "OQ-1 RESOLVED YES: _index sentinel implemented at keyring service 'photophore.channel', username '_index', value = JSON array of channel_ids. python-keyring has no enumerate-by-service API, so D-05 keystore-as-truth bootstrap requires this sentinel."
  - "OQ-4 RESOLVED: AT-A1 fixture committed structurally with phase:3 tag. Behavioral wire (channel-impersonation rejection by dispatch coordinator) is Phase 3 scope."
  - "OQ-5 RESOLVED: Flat photophore/core.py for shared types (Tier, ChannelId, ShadowId, AuditEntryId, ChannelState, AuditEventType). Avoids circular imports between audit/channels/classifier/shadow."
  - "Chain ordering uses rowid DESC (not timestamp+id DESC) for _last_entry_hash() because multiple entries can land in the same millisecond and UUID ordering doesn't match insertion order."
  - "Hypothesis flatmap strategy used for chain tamper tests: flatmap(n → integers(0..n-1)) generates correlated pairs with 100% valid examples (no assume() needed)."
  - "ResultPolicy public export: kept as _ResultPolicy private import from thermocline.envelope; decision to expose publicly deferred to Plan 02-03 when policy.author() needs it."
metrics:
  duration: "~55 minutes"
  completed: "2026-05-10"
  tasks_completed: 4
  files_created: 22
  files_modified: 2
  tests_written: 83
  hypothesis_examples: 200
---

# Phase 2 Plan 1: Package Scaffold + Audit + Channels Summary

**One-liner:** Greenfield `photophore` package with BLAKE3-chained append-only SQLite audit log, keystore-backed channel registry with _index sentinel and D-07 three-step write ordering, and `photophore audit|channel` CLI groups.

## What Was Built

### Confirmed Public API Surface

```python
from photophore import audit, channels, core, errors
from photophore.version import __version__

from photophore.audit import (
    AuditLog, AuditEntry, asdict, from_dict,
    AnchorTarget, NullAnchor, AnchorReceipt,
    AuditWriteError, AuditChainBrokenError, UnsupportedChainAlgoError,
)

from photophore.channels import (
    Channel, ChannelStore, ChannelState,
    ChannelStateError, UnauditedChannelError,
    bootstrap,
)

from photophore.core import (
    Tier, ChannelId, AuditEntryId, ShadowId, ChannelState, AuditEventType,
    KNOWN_EVENT_TYPES,
)

from photophore.errors import PhotophoreError, KeystoreUnavailableError  # re-export
```

Plan 02-02 imports `Tier` from `photophore.core`; Plan 02-03 imports `AuditLog` from `photophore.audit`. Phase 3 imports from both `photophore.audit` and `photophore.channels` for the dispatch coordinator.

### Resolved Decisions

**OQ-1 (index sentinel):** `_index` sentinel implemented at `photophore.channel:_index` in the keyring. Stores a JSON array of channel_ids. Updated atomically with channel create (inside D-07 step 1, before audit append). This is the only way D-05 keystore-as-truth bootstrap can detect channels that exist in the keystore but are missing from `channels.db`.

**OQ-4 (AT-A1 wiring timeline):** AT-A1 fixture committed structurally in Phase 2 with `phase: 3` tag in MANIFEST.yaml. The behavioral wire (dispatch coordinator rejecting a task envelope whose declared `key_scheme` mismatches the keystore record for the cited `channel_id`) lands in Phase 3 at the resolve-channel step.

**OQ-5 (core module strategy):** Flat `photophore/core.py` for Phase 2. All shared enums and NewTypes live here. Avoids circular imports where `audit` and `channels` both import from `core` but not from each other.

## Requirement Crosswalk

| Req ID | Test File | Test Function |
|--------|-----------|---------------|
| CHAN-01 | test_channels_lifecycle.py | test_create_channel_returns_proposed |
| CHAN-02 | test_channels_lifecycle.py | test_channel_state_machine_*, test_channel_proposed_to_suspended_is_invalid, test_channel_closed_is_terminal |
| CHAN-03 | test_channels_lifecycle.py | test_set_ceiling_lower_emits_ceiling_lowered, test_set_ceiling_raise_emits_ceiling_raised |
| CHAN-04 | test_channels_separation.py | test_audit_db_and_channels_db_are_different_files, test_channel_store_does_not_create_files_at_audit_db_path |
| CHAN-05 | test_channels_lifecycle.py | test_create_channel_appends_audit_entry_before_return |
| CHAN-06 | test_cli_channel.py | test_channel_list_json_returns_array, test_channel_show_json_returns_single_document |
| AUDIT-01 | test_audit_schema.py | test_delete_raises_integrity_error, test_update_raises_integrity_error |
| AUDIT-02 | test_audit_chain.py | test_every_entry_has_blake3_v1_algo_version, test_algo_registry_has_blake3_v1, test_compute_hash_by_version_unknown_raises |
| AUDIT-03 | test_audit_chain.py | test_chain_head_prev_hash_is_empty, test_second_entry_prev_hash_equals_first_entry_hash, test_third_entry_prev_hash_equals_second_entry_hash |
| AUDIT-04 | test_audit_query.py | test_audit04_dispatch_payload_round_trip |
| AUDIT-05 | test_audit_query.py | test_query_by_channel_id_filters_correctly, test_query_with_since_until_filter, test_query_shadow_id_filter_uses_json1, test_query_tier_filter_uses_json1 |
| AUDIT-06 | test_audit_export.py, test_cli_audit.py | test_export_includes_algo_version_on_every_line, test_audit_export_json_emits_json_lines_with_algo_version |
| AUDIT-07 | test_audit_anchor.py | test_anchor_target_is_runtime_checkable, test_audit_log_with_null_anchor_appends_successfully |
| AUDIT-08 | test_audit_chain_property.py | test_payload_tamper_invalidates_chain (100 examples), test_prev_hash_tamper_invalidates_chain (100 examples) |
| CLI-01 | test_cli_channel.py | All channel new/open/list/show/suspend/close/set-ceiling tests |
| CLI-02 | test_cli_audit.py | test_audit_query_json_emits_json_lines, test_audit_export_*, test_audit_verify_* |

## Conformance Fixtures

| Surface | File | Phase | Behavioral Wire |
|---------|------|-------|----------------|
| AT-A1 | AT-A1-channel-impersonation.json | 3 | Structural only; Phase 3 dispatch coordinator |
| AT-A4 | AT-A4-audit-log-tampering.json | 2 | test_audit_chain_property.py (Hypothesis, >=100 examples) |
| AT-A5 | AT-A5-trust-store-colocation.json | 2 | test_channels_separation.py (4 structural/behavioral tests) |

## Commits

| Task | Commit | Repo | Description |
|------|--------|------|-------------|
| 1 | ffccbb0 | photophore | Package scaffold + audit module |
| 2 | 84e7f63 | photophore | Channels module |
| 3 | 3c221e3 | photophore | CLI groups |
| 4 (test) | ec7ebc3 | photophore | AT-A5 separation test |
| 4 (fixtures) | aa3035a | thermocline | AT-A1/AT-A4/AT-A5 fixtures + MANIFEST |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Chain ordering used timestamp+id DESC instead of rowid DESC**
- **Found during:** Task 1 test run (test_third_entry_prev_hash_equals_second_entry_hash failed)
- **Issue:** Multiple entries landing in the same millisecond had the same timestamp. UUID ordering doesn't match insertion order, so `ORDER BY timestamp DESC, id DESC` returned the wrong "last" entry for `_last_entry_hash()`.
- **Fix:** Changed to `ORDER BY rowid DESC LIMIT 1` in `AuditLog._last_entry_hash()`. SQLite's rowid is monotonically increasing within a connection.
- **Files modified:** `photophore/python/src/photophore/audit/_store.py`
- **Commit:** ffccbb0

**2. [Rule 1 - Bug] Hypothesis test used assume() causing <100 valid examples**
- **Found during:** Task 1 Hypothesis test run (only 54 valid examples generated instead of 100)
- **Issue:** `@given(n_entries=..., tamper_index=...)` with `assume(tamper_index < n_entries)` caused 40% invalid examples. The search space was exhausted before 100 valid examples.
- **Fix:** Used `flatmap` strategy to generate correlated (n_entries, tamper_index) pairs: `st.integers(2..15).flatmap(lambda n: st.integers(0..n-1).map(lambda i: (n, i)))`. Expanded range to 2..15 gives 105 unique pairs (sum 1+2+...+14 = 105 > 100).
- **Files modified:** `photophore/python/tests/test_audit_chain_property.py`
- **Commit:** ffccbb0

**3. [Rule 1 - Bug] CLI test for broken chain tried to parse multi-line output as single JSON**
- **Found during:** Task 3 CLI test (test_audit_verify_json_broken_chain_exit_3)
- **Issue:** The verify command emits the JSON document AND then click emits the error message to stderr+stdout when using CliRunner. `json.loads(result.output)` failed on the concatenated string.
- **Fix:** Filter out "Error: ..." lines before JSON parsing in the test assertion.
- **Files modified:** `photophore/python/tests/test_cli_audit.py`
- **Commit:** 3c221e3

**4. [Rule 1 - Bug] AT-A5 fixture path resolution used wrong parent count**
- **Found during:** Task 4 test run (fixture load test was skipping)
- **Issue:** `test_dir.parent.parent.parent` walked too many levels, reaching `/Users/dom/Projects/dom` instead of `/Users/dom/Projects/dom/photophore`.
- **Fix:** Changed to `test_dir.parent.parent` (tests → python → photophore).
- **Files modified:** `photophore/python/tests/test_channels_separation.py`
- **Commit:** ec7ebc3

**5. [Rule 3 - Blocking] Thermocline editable install pointed to cleaned-up worktree path**
- **Found during:** Task 1 import verification
- **Issue:** The `_editable_impl_thermocline.pth` pointed to a worktree path that no longer existed (`/.claude/worktrees/agent-*/...`).
- **Fix:** Reinstalled thermocline from the actual source: `pip install -e /Users/dom/Projects/dom/thermocline/thermocline/python/`
- **Files modified:** System `.pth` file (myenv)

## Known Stubs

None. All public API methods are fully implemented. Plan 02-02 (classifier) and Plan 02-03 (shadow/policy) modules are not yet stubbed — they will be added in their respective plans.

## Threat Flags

No new threat surfaces introduced beyond those documented in the plan's `<threat_model>`. The three stores (keystore, channels.db, audit.db) are structurally separate as required by D-04 / AT-A5.

## Self-Check

All key files exist:
- photophore/python/pyproject.toml: FOUND
- photophore/python/src/photophore/audit/_schema.py: FOUND
- photophore/python/src/photophore/audit/_chain.py: FOUND
- photophore/python/src/photophore/channels/_keystore.py: FOUND
- thermocline/conformance/invalid/AT-A1-channel-impersonation.json: FOUND
- thermocline/conformance/invalid/AT-A4-audit-log-tampering.json: FOUND
- thermocline/conformance/invalid/AT-A5-trust-store-colocation.json: FOUND

All commits exist:
- ffccbb0 (photophore): Task 1 — package scaffold + audit module
- 84e7f63 (photophore): Task 2 — channels module
- 3c221e3 (photophore): Task 3 — CLI groups
- ec7ebc3 (photophore): Task 4 — AT-A5 separation test
- aa3035a (thermocline): Task 4 — conformance fixtures + MANIFEST

Full test suite: 83 unit tests + 200 Hypothesis examples = 283 total test invocations. All pass.
mypy --strict: 0 errors on 21 source files.
