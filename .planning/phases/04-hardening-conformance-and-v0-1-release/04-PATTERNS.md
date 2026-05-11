# Phase 04 Pattern Map

**Mapped:** 2026-05-11
**Files classified:** 56 (43 new, 13 modify)
**Analogs found (strong/role-match):** 43 / 56 ; **No analog (new-shape):** 13
**Cross-suite repos:** thermocline (cwd), photophore, seamount

## Reading Notes for Planner

- All paths below are **absolute** from `/Users/dom/Projects/dom/`. CONFLICT-01 in RESEARCH.md notes CONTEXT D-01 elides the doubled `thermocline/thermocline/` path; this PATTERNS.md uses the verified-on-disk paths.
- For each new file, the planner's task `<read_first>` block should list (a) the analog file, (b) the spec section the file binds, and (c) any cross-file shared pattern referenced in §"Cross-file invariants".
- The **15-line code excerpts** below are load-bearing: they show the exact import order, decorator stacking, allow-list shape, etc. that the new file must mimic. Longer excerpts are deferred to a Read-on-demand step in the plan.
- Where RESEARCH.md already provides a near-complete code skeleton (e.g., `SensitiveFilter`, `audit_cli_invocation` decorator), the §"Pattern to follow" defers to that section rather than duplicating it here.

---

## Files to Create / Modify

### Group A — AT-* negative tests (16 new files across 3 repos)

#### `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/at_negative/test_at_c1_envelope_tampering.py` (NEW)
- **Role:** test (AT-C surface, schema-level)
- **Closest existing analog:** `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/test_conformance_fixtures.py` (existing AT-C structural validation)
- **Pattern to follow:** Load fixture from `thermocline/conformance/invalid/AT-C1-replayed-envelope.json` (note the filename mismatch CONFLICT — see Pitfall 3 in RESEARCH); call `Task.parse_strict` OR `Verifier.verify` and assert the spec-defined failure. Mark with `@pytest.mark.at_surface("AT-C1")`. Module docstring opens with `AT-C1: <one-line failure mode from README>`.
- **Code excerpts:**
  ```python
  # analog: thermocline/thermocline/python/tests/test_conformance_fixtures.py:39-56
  _TESTS_DIR = Path(__file__).resolve().parent
  _THERMOCLINE_DIR = _TESTS_DIR.parents[1]
  CONFORMANCE_DIR = _THERMOCLINE_DIR / "conformance"
  EXPECTED_AT_C_SURFACES = {"AT-C1", "AT-C2", "AT-C3", "AT-C4", "AT-C5", "AT-C6"}

  def _load_json(path: Path) -> dict[str, Any]:
      return json.loads(path.read_text())
  ```
- **Differences from analog:** The analog tests *coverage of the corpus*; new files test *behavioral rejection* per surface — one assertion per file, marked with `@pytest.mark.at_surface(...)`.

#### `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/at_negative/test_at_c2_envelope_replay.py` (NEW)
- **Role:** test (AT-C2 replay)
- **Closest existing analog:** same as AT-C1 (`test_conformance_fixtures.py`)
- **Pattern to follow:** Identical to AT-C1 scaffold; fixture is `AT-C2-tampered-signature.json` (filename-vs-surface MISMATCH — RESEARCH Pitfall 3). Plan should either (a) rename in coordinated commit OR (b) parse `_at_surface` JSON key. **Recommended:** parse JSON key.
- **Differences from analog:** Test asserts `dispatch_async` rejects the second dispatch of the same `envelope_id` (replay cache MAY-clause per spec). If unimplemented, `@pytest.mark.skip(reason="...")` with rationale.

#### `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/at_negative/test_at_c3_shadow_correlation.py` (NEW)
- **Role:** test (AT-C3 shadow inference)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/test_shadow_uniqueness_property.py` (cross-repo)
- **Pattern to follow:** Reuse the inner-loop shadow-gen assertion from the analog — N calls with identical inputs produce N distinct shadow_ids. May `from photophore.shadow import generate` if cross-repo import is permissible in tests; otherwise, port the inner-loop assertion using thermocline-only types.
- **Differences from analog:** Lives in thermocline (envelope-side), uses fixture `AT-C3-leaky-shadow.json` for input.

#### `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/at_negative/test_at_c4_forged_dispatch_sig.py` (NEW)
- **Role:** test (AT-C4 forged signature)
- **Closest existing analog:** `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/test_identity_dispatch.py` (existing dispatch-signature tests) + fixture `AT-C4-key-scheme-mismatch.json`
- **Pattern to follow:** Construct or load an envelope with tampered signature bytes; assert `Verifier.verify(envelope) is None`. Pattern documented in BL-02 (Phase 1 LEARNINGS, see CHANGELOG entry at `thermocline/CHANGELOG.md:88-95`).
- **Differences from analog:** Negative path only; one assertion.

#### `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/at_negative/test_at_c5_result_policy_escalation.py` (NEW)
- **Role:** test (AT-C5 policy escalation)
- **Closest existing analog:** existing `test_conformance_fixtures.py` ParseError tests
- **Pattern to follow:** Fixture conflict — `AT-C5-unsupported-version.json` describes THERMO-07 not AT-C5. **Plan must add new fixture** `invalid/AT-C5-result-policy-modified.json` (signer canonicalizes one `result_policy`, forge serves a different one; verifier rejects).
- **Differences from analog:** New fixture creation required; existing analog only tests fixture *presence*, not behavior.

#### `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/at_negative/test_at_c6_key_compromise.py` (NEW)
- **Role:** test (AT-C6 documents-only)
- **Closest existing analog:** `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/test_identity_keystore_required.py` (IDENT-05 keystore-required guard, BL-03)
- **Pattern to follow:** Documents-only test marked `@pytest.mark.documents_only`. Asserts (a) `test_identity_keystore_required.py` exists in the test tree, (b) `BrineProvider.rotate()` API surface exists (BL-04). No envelope assertion needed.
- **Differences from analog:** Pure structural assertion; no runtime fixture replay.

#### `/Users/dom/Projects/dom/photophore/python/tests/at_negative/test_at_a1_compromised_sovereign.py` (NEW — re-export)
- **Role:** test (re-export shim)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/integration/test_e2e_at_a1_replay.py` (Phase 3 wired test)
- **Pattern to follow:** **Thin re-export** per CONTEXT D-01 Claude's-discretion note. Two-line file:
  ```python
  # Re-export so tools/at_coverage.py filename-scan sees AT-A1 covered.
  # Source-of-truth assertion lives in integration/test_e2e_at_a1_replay.py.
  from tests.integration.test_e2e_at_a1_replay import test_at_a1_replay_via_real_http  # noqa: F401
  ```
- **Differences from analog:** Zero behavioral logic; satisfies `at_coverage.py` filename pattern only.

#### `/Users/dom/Projects/dom/photophore/python/tests/at_negative/test_at_a2_shadow_correlation.py` (NEW)
- **Role:** test (AT-A2 shadow uniqueness)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/test_shadow_uniqueness_property.py`
- **Pattern to follow:** Re-export OR thin wrapper:
  ```python
  # analog: test_shadow_uniqueness_property.py:33-41
  ids = [
      generate(content, content_type, relevance=0.5).shadow.shadow_id
      for _ in range(100)
  ]
  assert len(set(ids)) == 100
  ```
- **Differences from analog:** Marked `@pytest.mark.at_surface("AT-A2")`; one assertion (not property-based).

#### `/Users/dom/Projects/dom/photophore/python/tests/at_negative/test_at_a3_classifier_evasion.py` (NEW)
- **Role:** test (AT-A3 classifier default)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/test_classifier_default_property.py`
- **Pattern to follow:** Single-case negative test (not property-based). RESEARCH §"Code Examples" line 1198 ships the full scaffold including docstring template.
- **Code excerpts:**
  ```python
  # analog: test_classifier_default_property.py:18-28
  @given(content=st.binary(min_size=0, max_size=10_000))
  @settings(max_examples=100, deadline=None)
  def test_unmatched_content_classifies_as_local(content: bytes) -> None:
      assume(b"@photophore:" not in content)
      result = classify(content, path=None, rules=None)
      assert result.tier == Tier.LOCAL
  ```
- **Differences from analog:** Single hand-crafted input (no `@given`); fixture file `AT-A3-classifier-evasion.json` MUST be created in `thermocline/conformance/invalid/`.

#### `/Users/dom/Projects/dom/photophore/python/tests/at_negative/test_at_a4_channel_mitm.py` (NEW)
- **Role:** test (AT-A4 MITM via signature verification)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/integration/test_e2e_forged_receipt.py`
- **Pattern to follow:** Mirror Phase 3 forged-receipt test — tamper envelope bytes mid-flight; verifier rejects. **Fixture rename:** existing `AT-A4-audit-log-tampering.json` is misnamed (Pitfall 3); planner must reconcile.
- **Differences from analog:** AT-A4 surface is *transit tampering*, not receipt forging; minor adaptation.

#### `/Users/dom/Projects/dom/photophore/python/tests/at_negative/test_at_a5_trust_store_tampering.py` (NEW)
- **Role:** test (AT-A5 keystore tamper detection)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/test_channels_separation.py` (three-store separation)
- **Pattern to follow:** Modify channel `ceiling` directly in ephemeral keystore namespace (test fixture); assert detection. **May skip-with-rationale** if v0.1 ships no tamper-detector.
- **Differences from analog:** Negative path; uses `seamount.ci-test.<uuid>` ephemeral namespace per `conftest.py` pattern.

#### `/Users/dom/Projects/dom/photophore/python/tests/at_negative/test_at_a6_audit_log_tamper.py` (NEW)
- **Role:** test (AT-A6 audit chain integrity)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/test_audit_chain_property.py`
- **Pattern to follow:** Re-export the existing payload-tamper test OR direct: tamper a byte; `verify_chain()` returns `(False, broken_at)`. Pattern from analog lines 79-93.
- **Code excerpts:**
  ```python
  # analog: test_audit_chain_property.py:78-93
  raw.execute("PRAGMA writable_schema=ON")
  raw.execute("DROP TRIGGER IF EXISTS entries_no_update")
  raw.execute("UPDATE entries SET payload = ? WHERE id = ?",
              ('{"tampered": true}', tamper_id))
  fresh_log = AuditLog(db_path)
  ok, broken_at = fresh_log.verify_chain()
  assert ok is False
  ```
- **Differences from analog:** Single case (not Hypothesis-driven); new fixture `AT-A6-audit-log-tampering.json` (envelope-shaped marker, even if test is in-process).

#### `/Users/dom/Projects/dom/seamount/conformance/at_negative/test_at_e1_malicious_payload.py` (NEW)
- **Role:** test (AT-E1 malformed payload, live forge POST)
- **Closest existing analog:** `/Users/dom/Projects/dom/seamount/conformance/forge_conformance/_harness.py` lines 321-336 (the SKIP markers RESEARCH calls out)
- **Pattern to follow:** **No close negative-test analog in seamount yet** — flag as new shape. Use Phase 3 `subprocess_forge` fixture pattern from `photophore/python/tests/integration/conftest.py:36-53`. POST malformed JSON; assert HTTP 400/422 with `MALFORMED_ENVELOPE` code.
- **Differences from analog:** First behavioral AT-E test in the suite; sets template for AT-E2..E5.

#### `/Users/dom/Projects/dom/seamount/conformance/at_negative/test_at_e2_resource_exhaustion.py` (NEW)
- **Role:** test (AT-E2 DoS)
- **Closest existing analog:** `seamount/conformance/at_negative/test_at_e1_malicious_payload.py` (sibling, also new)
- **Pattern to follow:** POST `digits=10_000_000` to pi-forge; assert HTTP 400 OR timeout within configured limit. **VERIFY** pi-forge has a size limit before writing assertion; if not, test surfaces a Phase 4 fix.
- **Differences from analog:** Per-forge specific; describe-forge does NOT compute digits — only pi-forge.

#### `/Users/dom/Projects/dom/seamount/conformance/at_negative/test_at_e3_tool_escape.py` (NEW)
- **Role:** test (AT-E3 documents-only)
- **Closest existing analog:** `seamount/conformance/at_negative/test_at_e1_malicious_payload.py` (sibling)
- **Pattern to follow:** Documents-only; mark `@pytest.mark.documents_only`. Assert (a) pi-forge accepts only `data.compute`, (b) describe-forge accepts only `description.generate`, (c) any other task type returns `UNSUPPORTED_TASK_TYPE`.
- **Differences from analog:** No live POST; pure structural assertion of `task_type` whitelist.

#### `/Users/dom/Projects/dom/seamount/conformance/at_negative/test_at_e4_forge_impersonation.py` (NEW)
- **Role:** test (AT-E4 forged receipt sig)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/integration/test_e2e_forged_receipt.py` (cross-repo)
- **Pattern to follow:** Spawn impersonator Flask app with different key; dispatch through Photophore; assert `DispatchError.RECEIPT_INVALID`. May re-export from photophore test if cross-repo import allowed in seamount/conformance tests.
- **Differences from analog:** Lives in seamount/conformance; needs cross-repo path setup OR thin re-export.

#### `/Users/dom/Projects/dom/seamount/conformance/at_negative/test_at_e5_timing_side_channel.py` (NEW)
- **Role:** test (AT-E5 documents-only)
- **Closest existing analog:** AT-E3 sibling (also documents-only)
- **Pattern to follow:** Mark `@pytest.mark.documents_only`. Assert (a) `pi-forge/server.py` does NOT log fine-grained per-request timing, (b) describe-forge output is deterministic w.r.t. input size.
- **Differences from analog:** Pure source-grep assertion (use `ast.parse` on `server.py` to walk for `time.perf_counter()` calls etc.).

---

### Group B — Property test edits + 1 new (5 files)

#### `/Users/dom/Projects/dom/photophore/python/tests/test_classifier_default_property.py` (MODIFY)
- **Role:** property test (CONF-03 #1)
- **Closest existing analog:** itself (in-place edit)
- **Pattern to follow:** Bump both `@settings(max_examples=100, ...)` to `200`. Add top-of-file comment `# CONF-03 invariant: classifier default fallthrough → LOCAL`.
- **Code excerpts:**
  ```python
  # current: test_classifier_default_property.py:19 and :32
  @settings(max_examples=100, deadline=None)
  # change to:
  @settings(max_examples=200, deadline=None)
  ```
- **Differences from analog:** Single-token diff; add module-level comment.

#### `/Users/dom/Projects/dom/photophore/python/tests/test_audit_chain_property.py` (MODIFY)
- **Role:** property test (CONF-03 #2)
- **Closest existing analog:** itself
- **Pattern to follow:** Bump `max_examples=100` to `200` on lines 58 and 104. Per Pitfall 1 (RESEARCH §"Common Pitfalls"), also widen integer-range strategy: change `st.integers(min_value=2, max_value=15)` → `max_value=20` so 200 examples = 200 distinct (n, tamper_index) pairs. Add top-of-file `# CONF-03 invariant: audit chain integrity (single-byte tamper invalidates)`.
- **Differences from analog:** Two-line strategy widening + two `max_examples` bumps + comment.

#### `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/test_canonical_properties.py` (MODIFY)
- **Role:** property test (CONF-03 #3)
- **Closest existing analog:** itself
- **Pattern to follow:** Property 1 already at 200 (line 72). Bump Properties 2 (line 93) and 5 (line 168) to 200. Add `@settings(max_examples=200)` to Properties 3 + 4 (currently default 100). Add `# CONF-03 invariant: canonical-JSON round-trip stability`.
- **Differences from analog:** Three `@settings` decorations to add/modify.

#### `/Users/dom/Projects/dom/photophore/python/tests/test_shadow_uniqueness_property.py` (MODIFY)
- **Role:** property test (CONF-03 #4)
- **Closest existing analog:** itself
- **Pattern to follow:** Bump `max_examples=100` to `200` on line 22. Add `# CONF-03 invariant: shadow ID uniqueness per dispatch`. Per Assumption A1, time the bump locally; if >1 min on CI runner, ship at 200 anyway (CONF-03 floor is 100).
- **Differences from analog:** Single-token diff + comment.

#### `/Users/dom/Projects/dom/photophore/python/tests/integration/test_property_dispatch_shadow_uniqueness.py` (NEW)
- **Role:** integration property test (CONF-03 #5, dispatch-integrated)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/integration/test_e2e_at_a1_replay.py` (subprocess_forge usage) + `test_shadow_uniqueness_property.py` (assertion shape)
- **Pattern to follow:** Combine `@pytest.mark.asyncio` + `@pytest.mark.parametrize("subprocess_forge", ["pi-forge"], indirect=True)` from AT-A1 pattern with the inner-loop assert from `test_shadow_uniqueness_property.py`. Mark `@pytest.mark.integration`.
- **Code excerpts:**
  ```python
  # analog: test_e2e_at_a1_replay.py:74-77
  @pytest.mark.asyncio
  @pytest.mark.parametrize("subprocess_forge", ["pi-forge"], indirect=True)
  async def test_property_dispatch_shadow_uniqueness(
      subprocess_forge: ForgeHandle, tmp_path: Path
  ) -> None:
      # Loop dispatch_async() N times against the same source envelope,
      # collect shadow_ids from intercepted DISPATCH_PRE entries, assert distinct.
  ```
- **Differences from analog:** Outer loop N=200; collect shadow_ids from `audit_log.query(event_type="dispatch.pre")` payloads.

---

### Group C — Coverage tools (5 new files)

#### `/Users/dom/Projects/dom/thermocline/tools/at_coverage.py` (NEW)
- **Role:** tool (AT-C* coverage gate)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/tools/ast_lint_network_isolation.py` (invocation/exit-code pattern) + `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/scripts/check_no_json_dumps.py` (path-resolution pattern)
- **Pattern to follow:** RESEARCH §"Code Examples" Example 2 line 1248 ships the full scaffold for the photophore variant; thermocline mirrors with `EXPECTED = {"AT-C1"..."AT-C6"}` and `PATTERN = re.compile(r"^test_at_c(\d+)_")`. Path resolution per `check_no_json_dumps.py:38`: `ROOT = Path(__file__).resolve().parents[1] / "thermocline" / "python" / "tests" / "at_negative"`.
- **Code excerpts:**
  ```python
  # analog: check_no_json_dumps.py:99-122
  def main(argv: list[str] | None = None) -> int:
      _ = argv
      findings = scan(ROOT)
      if findings:
          print("FAILED: ...", file=sys.stderr)
          return 1
      print("ok: ...", file=sys.stderr)
      return 0
  if __name__ == "__main__":
      sys.exit(main())
  ```
- **Differences from analog:** Filename-scan, not AST-walk; expected-set comparison instead of violation enumeration.

#### `/Users/dom/Projects/dom/photophore/tools/at_coverage.py` (NEW)
- **Role:** tool (AT-A* coverage gate)
- **Closest existing analog:** `thermocline/tools/at_coverage.py` (sibling, also new) + `photophore/tools/ast_lint_network_isolation.py:108-110` (entry-point pattern)
- **Pattern to follow:** Identical shape to thermocline variant; `EXPECTED = {"AT-A1"..."AT-A6"}`, `PATTERN = re.compile(r"^test_at_a(\d+)_")`. Per RESEARCH Example 2 (line 1248) which is the photophore version verbatim.
- **Differences from analog:** Only the EXPECTED set and PATTERN regex differ.

#### `/Users/dom/Projects/dom/seamount/tools/at_coverage.py` (NEW)
- **Role:** tool (AT-E* coverage gate)
- **Closest existing analog:** `photophore/tools/at_coverage.py` (sibling, also new)
- **Pattern to follow:** Same shape; `EXPECTED = {"AT-E1"..."AT-E5"}`, scans `seamount/conformance/at_negative/test_at_*.py`. **NEW DIR:** `seamount/tools/` does not yet exist.
- **Differences from analog:** Path roots from `seamount/conformance/at_negative/` (not `python/tests/`).

#### `/Users/dom/Projects/dom/thermocline/tools/at_coverage_total.py` (NEW)
- **Role:** tool (cross-repo 17/17 roll-up)
- **Closest existing analog:** **No analog — propose new shape.**
- **Pattern to follow:** Read `$THERMOCLINE_SUITE_ROOT` env var (default `$HOME/Projects/dom`). For each of three repos, invoke its `tools/at_coverage.py` via `subprocess.run` and union the found sets. Assert `len(union) == 17` and union equals the spec's full set.
- **Proposed structure** (~15 lines):
  ```python
  #!/usr/bin/env python3
  """Cross-repo AT-* coverage roll-up (17/17 union)."""
  from __future__ import annotations
  import os, subprocess, sys
  from pathlib import Path
  SUITE_ROOT = Path(os.environ.get("THERMOCLINE_SUITE_ROOT", Path.home()/"Projects"/"dom"))
  EXPECTED_TOTAL = 17
  def main() -> int:
      for repo, tool in [("thermocline","tools/at_coverage.py"),
                          ("photophore","tools/at_coverage.py"),
                          ("seamount","tools/at_coverage.py")]:
          r = subprocess.run([sys.executable, str(SUITE_ROOT/repo/tool)], check=False)
          if r.returncode != 0: return r.returncode
      print(f"ok: 17/17 AT-* coverage across suite.", file=sys.stderr)
      return 0
  if __name__ == "__main__": sys.exit(main())
  ```

#### `/Users/dom/Projects/dom/thermocline/tools/property_coverage.py` (NEW)
- **Role:** tool (4/4 property invariant check + `max_examples ≥ 200`)
- **Closest existing analog:** `thermocline/thermocline/python/src/thermocline/scripts/check_no_json_dumps.py` (AST-walk + lineno reporting)
- **Pattern to follow:** AST-parse each of the 4 (5) CONF-03 files; look for `# CONF-03 invariant:` comment AND parse `@settings(max_examples=N)` decorator literal; assert `N >= 200`. Per RESEARCH §"Property Test Inventory" line 217.
- **Proposed structure** (~15 lines):
  ```python
  #!/usr/bin/env python3
  """CONF-03 4/4 invariant + max_examples >= 200 gate."""
  from __future__ import annotations
  import ast, os, sys
  from pathlib import Path
  SUITE_ROOT = Path(os.environ.get("THERMOCLINE_SUITE_ROOT", Path.home()/"Projects"/"dom"))
  TARGETS = [
      SUITE_ROOT/"photophore/python/tests/test_classifier_default_property.py",
      SUITE_ROOT/"photophore/python/tests/test_audit_chain_property.py",
      SUITE_ROOT/"thermocline/thermocline/python/tests/test_canonical_properties.py",
      SUITE_ROOT/"photophore/python/tests/test_shadow_uniqueness_property.py",
  ]
  # For each: assert "CONF-03 invariant:" in text; walk @settings calls; assert max_examples >= 200.
  ```

---

### Group D — AST lints (`print(`) (3 new files)

#### `/Users/dom/Projects/dom/thermocline/tools/ast_lint_no_print.py` (NEW)
- **Role:** AST lint (CONF-06)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/tools/ast_lint_network_isolation.py`
- **Pattern to follow:** Direct mirror of `ast_lint_network_isolation.py` structure: `PROTECTED_FRAGMENTS`, `ALLOWED_FRAGMENTS`, `check_file`, `scan`, `main`. RESEARCH §`print( AST Lint Scope` lines 597-633 ships the full skeleton including the 5-entry allow-list (forge `server.py` + `__main__.py` + scripts dir + tests + examples).
- **Code excerpts:**
  ```python
  # analog: ast_lint_network_isolation.py:35-53
  PROTECTED_FRAGMENTS: tuple[str, ...] = (
      "/src/thermocline/", "/src/photophore/",
  )
  ALLOWED_FRAGMENTS: tuple[str, ...] = (
      "/src/thermocline/scripts/", "/src/photophore/cli/",
      "/tests/", "/examples/",
  )
  def is_allowed(path: Path) -> bool:
      return any(frag in path.as_posix() for frag in ALLOWED_FRAGMENTS)
  ```
- **Differences from analog:** Visitor matches `ast.Call` with `ast.Name(id="print")` (not `ast.Import`); FORBIDDEN set is just `{"print"}`; add `ALLOWED_FORGE_FRAGMENTS` per CONFLICT-03 + RESEARCH §"print( Lint Scope".

#### `/Users/dom/Projects/dom/photophore/tools/ast_lint_no_print.py` (NEW)
- **Role:** AST lint (CONF-06)
- **Closest existing analog:** sibling `thermocline/tools/ast_lint_no_print.py` + `photophore/tools/ast_lint_network_isolation.py` (same repo)
- **Pattern to follow:** Identical content to thermocline sibling. Per CONTEXT D-09 + RESEARCH Assumption A7: three identical files preferred over one shared (less coupling).
- **Differences from analog:** None — byte-identical copy.

#### `/Users/dom/Projects/dom/seamount/tools/ast_lint_no_print.py` (NEW)
- **Role:** AST lint (CONF-06)
- **Closest existing analog:** sibling. **NEW DIR:** `seamount/tools/` does not yet exist.
- **Pattern to follow:** Identical copy. ALLOWED_FORGE_FRAGMENTS critical here because `seamount/pi-forge/pi_forge/__main__.py` line 52, 58, 62, 73 + `seamount/pi-forge/server.py` lines 171-173 + describe-forge equivalents all use `print()` (the `PIFORGE_READY port=` marker is contractual with subprocess_forge per Assumption A12).
- **Differences from analog:** None — byte-identical copy.

---

### Group E — `cli_invocation` audit retrofit (3 modify + 1 new)

#### `/Users/dom/Projects/dom/photophore/python/src/photophore/audit/__init__.py` (MODIFY)
- **Role:** source (export `append_cli_invocation` helper)
- **Closest existing analog:** itself
- **Pattern to follow:** Add `from ._cli_invocation import append_cli_invocation` and append to `__all__`. Existing `__all__` shape at lines 19-30.
- **Code excerpts:**
  ```python
  # analog: audit/__init__.py:19-30
  __all__ = [
      "AuditLog", "AuditEntry", ...
      "append_cli_invocation",  # NEW
  ]
  ```
- **Differences from analog:** One import line + one `__all__` entry.

#### `/Users/dom/Projects/dom/photophore/python/src/photophore/audit/_cli_invocation.py` (NEW)
- **Role:** source (helper that calls `AuditLog.append` with `event_type=AuditEventType.CLI_INVOKED`)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/src/photophore/audit/_store.py:62-110` (`AuditLog.append` signature)
- **Pattern to follow:** Thin wrapper — see RESEARCH §"cli_invocation Audit Retrofit" line 431-453 for the full helper function shape (10 lines).
- **Code excerpts:**
  ```python
  # analog: _store.py:62-91 (append signature + KNOWN_EVENT_TYPES gate)
  if event_type not in KNOWN_EVENT_TYPES:
      raise AuditWriteError(...)
  # CLI_INVOKED is already in KNOWN_EVENT_TYPES at core.py:102 — no enum edit needed.
  ```
- **Differences from analog:** No new enum/schema changes — the slot is pre-shipped.

#### `/Users/dom/Projects/dom/photophore/python/src/photophore/cli/__init__.py` (MODIFY)
- **Role:** source (wrap click group + every leaf subcommand with `@audit_cli_invocation`)
- **Closest existing analog:** itself (current click group at lines 38-66)
- **Pattern to follow:** Per RESEARCH §"cli_invocation Audit Retrofit" lines 456-518 — full decorator + helper code. Decoration order critical per Pitfall 6: `@click.command()` outermost, `@audit_cli_invocation("name")` inside, `@click.pass_context` innermost.
- **Code excerpts:**
  ```python
  # current cli/__init__.py:38-56
  @click.group()
  @click.option("--json", ...)
  @click.option("--data-dir", ...)
  @click.version_option(package_name="photophore")
  @click.pass_context
  def photophore(ctx: click.Context, output_json: bool, data_dir: str) -> None:
      ...
  ```
- **Differences from analog:** Add decorator import + wrap each `add_command(...)` target (or wrap subcommand decorators in each `*_cmds.py`).

#### `/Users/dom/Projects/dom/photophore/python/src/photophore/cli/audit_cmds.py`, `channel_cmds.py`, `classify_cmds.py`, `policy_cmds.py`, `dispatch_cmds.py` (MODIFY each)
- **Role:** source (per-subcommand `@audit_cli_invocation("...")` decoration)
- **Closest existing analog:** `audit_cmds.py:32-50` (existing `@audit.command("query")` shape)
- **Pattern to follow:** Insert `@audit_cli_invocation("audit.query")` between `@audit.command("query")` and `@click.option(...)` decorators. Apply to every leaf command.
- **Code excerpts:**
  ```python
  # analog: audit_cmds.py:32-41
  @audit.command("query")
  @click.option("--channel", "channel_id", default=None, ...)
  # ... more options ...
  @click.pass_context
  def query(ctx: click.Context, channel_id: str | None, ...) -> None:
      ...
  # After Phase 4:
  @audit.command("query")
  @audit_cli_invocation("audit.query")
  @click.option(...)
  ...
  @click.pass_context
  def query(...): ...
  ```
- **Differences from analog:** Decorator-only insertion; no signature changes.

#### `/Users/dom/Projects/dom/photophore/python/tests/test_cli_invocation_audit.py` (NEW)
- **Role:** test (verify CLI-06 — every subcommand emits one CLI_INVOKED entry)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/test_cli_audit.py` (existing CLI test using `CliRunner`)
- **Pattern to follow:** Use `click.testing.CliRunner`; invoke each subcommand; query `audit.db`; assert one `cli.invoked` entry per invocation.
- **Differences from analog:** Asserts on `event_type=AuditEventType.CLI_INVOKED` rows (not channel/dispatch rows).

---

### Group F — CLI-07 error-message tweaks (3 modify + 1 new)

#### `/Users/dom/Projects/dom/photophore/python/src/photophore/cli/dispatch_cmds.py` (MODIFY)
- **Role:** source (D-08 error message augmentation)
- **Closest existing analog:** itself, lines 89-96
- **Pattern to follow:** Augment the f-string at lines 93-95 to include `(tier=X, reason=Y)` when `exc.subcode in {POLICY_VIOLATED, CLASSIFICATION_FAILED}`. Requires either a new `BlockedBlock` NamedTuple field on `DispatchError` (RESEARCH A5 recommendation) OR a string-format-only tweak (CONTEXT D-08 says "no API change").
- **Code excerpts:**
  ```python
  # current: dispatch_cmds.py:89-96
  audit_note = (f" audit entry: {exc.audit_entry_hash}." if exc.audit_entry_hash else "")
  click.echo(
      f"error: dispatch failed ({exc.subcode}) at step {exc.stage}: "
      f"{exc}. retryable: {str(exc.retryable).lower()}.{audit_note}"
  )
  # After Phase 4 (string-only path):
  tier_reason = f" (tier={exc.blocked_tier}, reason={exc.blocked_reason})" if exc.blocked_tier else ""
  click.echo(f"...: blocked block: ...{tier_reason}. ...")
  ```
- **Differences from analog:** Conditional suffix insertion only.

#### `/Users/dom/Projects/dom/photophore/python/src/photophore/cli/classify_cmds.py` (MODIFY)
- **Role:** source (D-08 error-path augmentation)
- **Closest existing analog:** itself (per Phase 2 CLI-04, success path already emits `(tier, reason)`)
- **Pattern to follow:** Find `RulesConfigError` raise sites; augment messages with failing rule's tier/reason when identifiable.
- **Differences from analog:** Error-path message strings only.

#### `/Users/dom/Projects/dom/photophore/python/src/photophore/cli/policy_cmds.py` (MODIFY)
- **Role:** source (D-08 error-path augmentation)
- **Closest existing analog:** itself
- **Pattern to follow:** Find `PolicyError` raise sites in `policy preview`; append offending block's `(tier, reason)`.
- **Differences from analog:** Same shape as classify_cmds tweak.

#### `/Users/dom/Projects/dom/photophore/python/tests/test_cli_error_messages.py` (NEW)
- **Role:** test (snapshot CLI error output)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/python/tests/test_cli_audit.py` (CliRunner usage)
- **Pattern to follow:** `CliRunner.invoke()`; `assert "(tier=" in result.output` per RESEARCH §"CLI-07 Error Message Retrofit" line 535.
- **Differences from analog:** Snapshot-style string assertion on `result.output`.

---

### Group G — `Sensitive[T]` retrofit (1 new module + 2 new tests)

#### `/Users/dom/Projects/dom/photophore/python/src/photophore/logging.py` (NEW)
- **Role:** source (SensitiveFilter + configure_logging)
- **Closest existing analog:** **No existing photophore logger config.** Closest in suite: `/Users/dom/Projects/dom/thermocline/thermocline/python/src/thermocline/sensitive.py` (the `Sensitive[T]` consumer pattern).
- **Pattern to follow:** RESEARCH §"SensitiveFilter Logging Filter" lines 656-719 ships the full module verbatim (~60 lines). Uses `logging.Filter` stdlib pattern; walks `record.__dict__` and `record.args` for `Sensitive` instances.
- **Code excerpts:**
  ```python
  # analog (the consumer side — sensitive.py:34-63):
  class Sensitive(Generic[T]):
      __slots__ = ("_value",)
      def reveal(self) -> T: return self._value
      def __repr__(self) -> str:
          return f"<Sensitive: {type(self._value).__name__}>"
  ```
- **Differences from analog:** New filter wraps detection — see RESEARCH for full code.

#### `/Users/dom/Projects/dom/photophore/python/tests/test_logging_filter.py` (NEW)
- **Role:** test (verify SensitiveFilter drops Sensitive values)
- **Closest existing analog:** `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/test_sensitive.py` (existing Sensitive redaction tests)
- **Pattern to follow:** Use pytest `caplog` fixture; assert `logger.info("dispatch", extra={"envelope": Sensitive(b"private")})` produces `<REDACTED>` and no `b"private"` substring.
- **Differences from analog:** Cross-module: imports both `photophore.logging` and `thermocline.sensitive`.

#### `/Users/dom/Projects/dom/photophore/python/tests/test_sensitive_redaction.py` (NEW)
- **Role:** test (enumerate `Sensitive`-typed fields; assert redacted-rendering)
- **Closest existing analog:** `/Users/dom/Projects/dom/thermocline/thermocline/python/tests/test_sensitive.py` (existing test of `Sensitive[T]` behavior in thermocline)
- **Pattern to follow:** Enumerate Pydantic models with `Sensitive[*]` fields via model introspection; assert `repr(populated_model)` contains `<Sensitive:` for each.
- **Differences from analog:** Walks `photophore.audit._types.AuditEntry` and any Sensitive-bearing field; cross-suite import of `Sensitive` from thermocline.

#### `/Users/dom/Projects/dom/photophore/python/src/photophore/audit/_store.py` (MODIFY — runtime guard)
- **Role:** source (defense-in-depth: reject `Sensitive` in audit payload)
- **Closest existing analog:** itself, lines 81-86 (existing `KNOWN_EVENT_TYPES` validation)
- **Pattern to follow:** Add `_assert_no_sensitive(payload)` helper called inside `append()`. RESEARCH §"Sensitive[T] Sweep" lines 564-577 ships the helper.
- **Code excerpts:**
  ```python
  # analog: _store.py:81-86 (existing validation pattern)
  if event_type not in KNOWN_EVENT_TYPES:
      raise AuditWriteError(
          f"unknown event_type {event_type!r}; ...",
          code="AUDIT_WRITE_FAILED",
      )
  # New guard mirrors this shape; raises AuditWriteError with code="AUDIT_SENSITIVE_LEAK".
  ```
- **Differences from analog:** Walks dict recursively; defensive — not a new public API.

---

### Group H — ADRs (7 new files + 3 index files)

#### `/Users/dom/Projects/dom/thermocline/docs/adr/ADR-0001-python-3-11-as-primary-language.md` (NEW)
- **Role:** doc (ADR; one-page MADR-lite)
- **Closest existing analog:** **No existing ADRs in suite.** Closest: the ADR template inline in RESEARCH §"ADR Landings" Example 3 (line 1293) — a full MADR-lite example.
- **Pattern to follow:** Four headings: `## Context`, `## Decision`, `## Consequences`, `## References`. Status line at top: `**Status:** Accepted · 2026-MM-DD`. Source material from PROJECT.md Key Decisions table line 108 + CLAUDE.md "Language" entry.
- **Differences from analog:** Brand new — no in-suite precedent. RESEARCH Example 3 (ADR-0003 source) is the byte-level shape to mirror.

#### `/Users/dom/Projects/dom/thermocline/docs/adr/ADR-0002-pydantic-v2-lock-in.md` (NEW)
- **Role:** doc (ADR)
- **Closest existing analog:** sibling `ADR-0001` (also new)
- **Pattern to follow:** Same MADR-lite shape. Source: PROJECT.md line 113 + pyproject.toml `pydantic>=2.7,<3.0` pin.

#### `/Users/dom/Projects/dom/thermocline/docs/adr/ADR-0003-single-canonical-json-path.md` (NEW)
- **Role:** doc (ADR)
- **Closest existing analog:** sibling. **RESEARCH Example 3 (lines 1294-1334)** ships this exact ADR's prose verbatim.
- **Pattern to follow:** Copy verbatim from RESEARCH.
- **Differences from analog:** None — RESEARCH ships it.

#### `/Users/dom/Projects/dom/thermocline/docs/adr/ADR-0004-blake3-with-algo-version.md` (NEW)
- **Role:** doc (ADR)
- **Pattern to follow:** MADR-lite. Source: AUDIT-02 + `_chain.py` `ALGO_VERSION_DEFAULT`.

#### `/Users/dom/Projects/dom/thermocline/docs/adr/ADR-0005-no-in-process-key-material.md` (NEW)
- **Role:** doc (ADR; cross-referenced from photophore README)
- **Pattern to follow:** MADR-lite. Source: IDENT-02, IDENT-05; Phase 1 BL-03 (CHANGELOG.md:96-101).

#### `/Users/dom/Projects/dom/photophore/docs/adr/ADR-0001-trust-store-separation-from-audit-log.md` (NEW)
- **Role:** doc (ADR)
- **Pattern to follow:** MADR-lite. Source: CHAN-04 + Phase 2 D-04 three-store model + existing `test_channels_separation.py`.

#### `/Users/dom/Projects/dom/photophore/docs/adr/ADR-0002-no-shadow-caching.md` (NEW)
- **Role:** doc (ADR)
- **Pattern to follow:** MADR-lite. Source: SHADOW-06 + `test_shadow_no_caching.py`.

#### `/Users/dom/Projects/dom/thermocline/docs/adr/index.md` (NEW)
- **Role:** doc (one-line bulleted list)
- **Closest existing analog:** **No analog — propose new shape.**
- **Proposed structure:**
  ```markdown
  # Architecture Decision Records (Thermocline)

  - [ADR-0001: Python 3.11 as primary language](ADR-0001-python-3-11-as-primary-language.md) — Accepted, 2026-MM-DD
  - [ADR-0002: Pydantic v2 lock-in](ADR-0002-pydantic-v2-lock-in.md) — Accepted, 2026-MM-DD
  - ... (5 entries total)
  ```

#### `/Users/dom/Projects/dom/photophore/docs/adr/index.md` (NEW)
- Same shape as thermocline `index.md`; 2 ADRs.

#### `/Users/dom/Projects/dom/seamount/docs/adr/index.md` (NEW)
- Cross-ref only (no own ADRs); links to relevant thermocline ADRs via `../../thermocline/docs/adr/...`. Per CONTEXT D-03 — seamount has 0 own ADRs.

---

### Group I — Install/ops docs (7 new files)

#### `/Users/dom/Projects/dom/thermocline/docs/install.md` (NEW)
- **Role:** doc (per-repo install)
- **Closest existing analog:** `/Users/dom/Projects/dom/thermocline/README.md` (existing top-level install section, if any)
- **Pattern to follow:** ~200-300 lines; system requirements (Python 3.11+, macOS 12+ recommended); `pip install -e thermocline/python`; keystore prereqs; Apple Silicon Secure Enclave v0.2 known-limitation note per D-11.
- **Differences from analog:** New file; README stays as overview, docs/install.md is depth.

#### `/Users/dom/Projects/dom/thermocline/docs/ops.md` (NEW)
- **Role:** doc (placeholder; library has no ops surface)
- **Closest existing analog:** none
- **Pattern to follow:** Minimal placeholder: "thermocline-py is a library; no ops surface. See photophore/docs/ops.md for audit log + channel ops."

#### `/Users/dom/Projects/dom/thermocline/docs/quickstart.md` (NEW — the 30-minute CONF-07 walkthrough)
- **Role:** doc (cross-repo walkthrough)
- **Closest existing analog:** **No analog — propose new shape.** RESEARCH §"Ops Docs Scope" lines 344-407 ships the verbatim command sequence + section structure.
- **Pattern to follow:** 10 sections per RESEARCH line 394-404 (Prerequisites → Clone → Install → Keystore setup → Start forge → Create channel → Dispatch → Inspect audit → Cleanup → Next steps). macOS first-prompt Keychain gotchas documented per RESEARCH line 389-392.
- **Proposed structure:** See RESEARCH §"Ops Docs Scope" lines 344-407 verbatim.

#### `/Users/dom/Projects/dom/photophore/docs/install.md` (NEW)
- **Role:** doc
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/README.md` + sibling `thermocline/docs/install.md`
- **Pattern to follow:** Same shape as thermocline install.md. Depends on `thermocline-py`; `pip install -e ../thermocline/thermocline/python && pip install -e .`.

#### `/Users/dom/Projects/dom/photophore/docs/ops.md` (NEW)
- **Role:** doc (chain archival, audit verify, channel ceiling rotation, channel close)
- **Closest existing analog:** none in repo; closest reference: existing `audit_cmds.py` + `channel_cmds.py` subcommand surface.
- **Pattern to follow:** Per-subcommand description with example invocation. **VERIFY** (Open Question 3) that `photophore audit archive` exists before documenting it.

#### `/Users/dom/Projects/dom/seamount/pi-forge/docs/install.md` (NEW)
- **Role:** doc (per-forge install)
- **Closest existing analog:** `/Users/dom/Projects/dom/seamount/pi-forge/README.md`
- **Pattern to follow:** Keystore init walkthrough; `--keyring-service seamount.piforge` namespace.

#### `/Users/dom/Projects/dom/seamount/describe-forge/docs/install.md` (NEW)
- **Role:** doc
- **Pattern to follow:** Same as pi-forge; tier-1 shadow contract reminder.

#### `/Users/dom/Projects/dom/seamount/conformance/docs/install.md` (NEW)
- **Role:** doc (harness install + arbitrary-forge runner)
- **Closest existing analog:** `/Users/dom/Projects/dom/seamount/conformance/README.md`
- **Pattern to follow:** `pip install -e .[dev]` + `python -m forge_conformance --target URL --role ROLE`.

---

### Group J — README amendments (3 modify)

#### `/Users/dom/Projects/dom/thermocline/README.md` (MODIFY — SP-3.3-01..03 + ADR section)
- **Role:** spec amendment + doc cross-ref
- **Closest existing analog:** itself + the THERMO-01 pattern documented in `thermocline/CHANGELOG.md:12-60`
- **Pattern to follow:** Three normative paragraphs (verbatim text in CONTEXT D-02). Add §"Architecture Decision Records" linking `docs/adr/index.md`.
- **Differences from analog:** Per CONFLICT-02 — Phase 3 03-03-SUMMARY called these coordinator-internal; D-02 reverses to spec patches. CHANGELOG `## [0.3.1]` entry must note the reversal.

#### `/Users/dom/Projects/dom/photophore/README.md` (MODIFY)
- **Role:** doc cross-ref (ADR section + Documentation section)
- **Closest existing analog:** itself; **RESEARCH Example 4** (line 1336) ships the exact ADR cross-ref block.
- **Pattern to follow:** Append §"Architecture Decision Records" (2 own + 4 inherited cross-refs).
- **Code excerpts:**
  ```markdown
  ## Architecture Decision Records

  ### Photophore-specific
  - [ADR-0001: Trust-store separation from audit log](docs/adr/ADR-0001-trust-store-separation-from-audit-log.md)
  - [ADR-0002: No shadow caching](docs/adr/ADR-0002-no-shadow-caching.md)

  ### Inherited from `thermocline-py`
  - [ADR-0001: Python 3.11 as primary language](../thermocline/docs/adr/ADR-0001-python-3-11-as-primary-language.md)
  - [ADR-0003: Single canonical JSON path](../thermocline/docs/adr/...)
  - [ADR-0004: BLAKE3 with `algo_version` chain](../thermocline/docs/adr/...)
  - [ADR-0005: No in-process key material](../thermocline/docs/adr/...)
  ```

#### `/Users/dom/Projects/dom/seamount/README.md` (MODIFY)
- **Role:** doc cross-ref
- **Pattern to follow:** Same shape as photophore README; cross-refs ADR-0001, ADR-0003, ADR-0005 from thermocline. No own ADRs.

---

### Group K — CHANGELOGs (1 modify + 2 new)

#### `/Users/dom/Projects/dom/thermocline/thermocline/CHANGELOG.md` (MODIFY)
- **Role:** changelog (extend with `## [0.3.1]` dated + `## [0.1.0]` suite milestone)
- **Closest existing analog:** itself, lines 12-105 (existing `## v0.3.1 (in progress)` section)
- **Pattern to follow:** Newest-on-top per Keep-a-Changelog; date the existing `v0.3.1` heading; add new `## [0.1.0] - 2026-MM-DD` section using the Keep-a-Changelog-lite template (Added / Implemented / Deferred / Known limitations).
- **Code excerpts:**
  ```markdown
  # current line 12: `## v0.3.1 (in progress — Phase 1 + Phase 2)`
  # change to: `## [0.3.1] - 2026-MM-DD` and prepend `## [0.1.0] - 2026-MM-DD` above.
  ```
- **Differences from analog:** Date the in-progress heading; prepend the suite-milestone section.

#### `/Users/dom/Projects/dom/photophore/CHANGELOG.md` (NEW)
- **Role:** changelog (new file)
- **Closest existing analog:** `/Users/dom/Projects/dom/thermocline/thermocline/CHANGELOG.md` (sibling-repo pattern)
- **Pattern to follow:** Keep-a-Changelog-lite template per RESEARCH §"Release Script + CHANGELOGs" lines 853-884 (full template inline). Per-repo Implemented section per RESEARCH line 886-890.

#### `/Users/dom/Projects/dom/seamount/CHANGELOG.md` (NEW)
- **Role:** changelog (new file)
- **Pattern to follow:** Same Keep-a-Changelog-lite template. Seamount Implemented section: FORGE-01..05.

---

### Group L — Release script + tools dir bootstrapping (1 new file)

#### `/Users/dom/Projects/dom/thermocline/scripts/tag-v0.1.0.sh` (NEW)
- **Role:** bash (release coordination)
- **Closest existing analog:** **No analog — propose new shape.** RESEARCH §"Release Script + CHANGELOGs" lines 728-844 ships the full ~110-line bash script.
- **Pattern to follow:** Use the RESEARCH-supplied script verbatim. Honors POSIX BRE (no `grep -P`); detects `gsed` is unnecessary because no in-place edits are performed; uses `date -u +%Y-%m-%d` for portability.
- **Differences from analog:** None — RESEARCH ships it.

---

### Group M — CI workflows (1 new + 2 modify)

#### `/Users/dom/Projects/dom/thermocline/.github/workflows/ci.yml` (NEW)
- **Role:** config (GitHub Actions workflow)
- **Closest existing analog:** `/Users/dom/Projects/dom/photophore/.github/workflows/ci.yml` (verified — see lines 1-81)
- **Pattern to follow:** Mirror the two-job split (`lint-and-test` on ubuntu-latest + `keystore-tests` on macos-latest). RESEARCH §"CI Gate Inventory" lines 266-314 ships the full template.
- **Code excerpts:**
  ```yaml
  # analog: photophore/.github/workflows/ci.yml:1-37 (job shape)
  name: photophore CI
  on:
    push: {branches: [main]}
    pull_request: {branches: [main]}
  jobs:
    lint-and-test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
          with: {path: photophore}
        - uses: actions/setup-python@v5
          with: {python-version: "3.11"}
        - name: Install
          working-directory: photophore/python
          run: pip install -e .[dev]
  ```
- **Differences from analog:** New file. Working dirs adjusted for `thermocline/python`. Add new gates per CONF-04 final list (ruff, mypy --strict, pip-audit, network-isolation lint, print-lint, canonical-JSON lint, at_coverage, at_coverage_total, property_coverage, pytest).

#### `/Users/dom/Projects/dom/photophore/.github/workflows/ci.yml` (MODIFY)
- **Role:** config
- **Pattern to follow:** Insert new steps before `Pytest (non-integration)`: `python tools/ast_lint_no_print.py`, `python tools/at_coverage.py`. Existing two-job shape preserved.
- **Differences from analog:** Additive steps only.

#### `/Users/dom/Projects/dom/seamount/.github/workflows/ci.yml` (MODIFY)
- **Role:** config
- **Pattern to follow:** Add `python tools/ast_lint_no_print.py` + `python tools/at_coverage.py` to each existing job (or to the harness job). CONFLICT-04 resolution: either add `[tool.mypy] strict = true` to forge pyprojects OR document exemption.

---

### Group N — Conformance fixtures (7 new fixtures + MANIFEST edit)

#### `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-A3-classifier-evasion.json` (NEW)
- **Role:** fixture (test corpus)
- **Closest existing analog:** `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-A2-shadow-correlation.json` (existing AT-A2 fixture)
- **Pattern to follow:** Mirror AT-A2 envelope shape; payload is a crafted-benign content block with hidden credential-like substring. Include `_at_surface` metadata key.
- **Differences from analog:** Different content payload; same envelope wrapper.

#### `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-A6-audit-log-tampering.json` (NEW)
- **Role:** fixture
- **Closest existing analog:** existing `AT-A4-audit-log-tampering.json` (which is misnamed per Pitfall 3 — actually AT-A6 content)
- **Pattern to follow:** Either rename existing file OR add new with corrected name. Recommended: dual-fixture approach (deprecate-then-add) per RESEARCH Pitfall 3.

#### `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-E1-malicious-payload.json` (NEW)
- **Role:** fixture
- **Closest existing analog:** any existing `AT-C*` fixture (the envelope-wrapper shape)
- **Pattern to follow:** Intentionally malformed JSON OR oversized field OR unknown top-level key.

#### `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-E2-resource-exhaustion.json` (NEW)
- **Role:** fixture
- **Pattern to follow:** Valid envelope structure; task asks for 10M digits of π (`{"task_type": "data.compute", "parameters": {"digits": 10000000}}`).

#### `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-E3-tool-escape.json` (NEW)
- **Role:** fixture (marker)
- **Pattern to follow:** Empty/marker fixture; test is documents-only.

#### `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-E4-forge-impersonation.json` (NEW)
- **Role:** fixture
- **Closest existing analog:** AT-C4 (key-scheme mismatch)
- **Pattern to follow:** Valid envelope signed with wrong (impersonator) key; verifier rejects.

#### `/Users/dom/Projects/dom/thermocline/thermocline/conformance/invalid/AT-E5-timing-side-channel.json` (NEW)
- **Role:** fixture (marker)
- **Pattern to follow:** Empty/marker fixture; test is documents-only.

#### `/Users/dom/Projects/dom/thermocline/thermocline/conformance/MANIFEST.yaml` (MODIFY — backfill)
- **Role:** config (fixture index)
- **Closest existing analog:** itself, lines 31-39 (existing AT-A1 `fixtures:` entry)
- **Pattern to follow:** Add 7 new `fixtures:` entries (AT-A3, AT-A6, AT-E1..E5) with `phase: 4, phase_wired: 4`. Backfill missing AT-A2, AT-A4, AT-A5 with `phase: 2, phase_wired: 4`. Each entry: `file`, `at_surface`, `phase`, `phase_wired`, `wired_test_path`, `wired_assertion`, `expect_error_code`, `notes` — exact shape per existing AT-A1 entry.
- **Code excerpts:**
  ```yaml
  # analog: MANIFEST.yaml:32-39
  fixtures:
    - file: invalid/AT-A1-channel-impersonation.json
      at_surface: AT-A1
      phase: 3
      phase_wired: 3
      wired_test_path: "photophore/python/tests/integration/test_e2e_at_a1_replay.py"
      wired_assertion: "test_at_a1_replay_via_real_http"
      expect_error_code: CHANNEL_IMPERSONATION
      notes: "Phase 3 wire-in complete; ..."
  ```
- **Differences from analog:** Add 10 entries (7 new fixtures + 3 backfills); also add `- phase: 4` description block to `phases_covered` list at top.

---

## New patterns proposed (no existing analog)

### `at_coverage_total.py` (cross-repo roll-up)
- **Why no analog:** First cross-repo CI gate in the suite — all existing CI gates are per-repo.
- **Proposed structure:** See Group C entry above. Reads `$THERMOCLINE_SUITE_ROOT`; subprocess-invokes each repo's `at_coverage.py`; asserts union == 17. ~15 lines.

### `property_coverage.py` (CONF-03 4/4 gate)
- **Why no analog:** AST-walks four specific files for invariant comments + decorator literals; not a pattern any existing tool uses.
- **Proposed structure:** See Group C entry above. AST-parse each TARGETS file; assert `# CONF-03 invariant:` comment present; assert every `@settings(max_examples=N)` has `N >= 200`. ~30 lines.

### `tag-v0.1.0.sh` (POSIX-portable release coordination)
- **Why no analog:** No release scripts exist anywhere in the three-repo suite.
- **Proposed structure:** RESEARCH §"Release Script + CHANGELOGs" lines 728-844 ships the verbatim ~110-line bash script. Uses `set -euo pipefail`, BSD-compatible commands only, supports `--dry-run`.

### MADR-lite ADR template
- **Why no analog:** No existing ADRs in the suite.
- **Proposed structure:** RESEARCH §"Code Examples" Example 3 (lines 1294-1334) ships the verbatim ADR-0003 template. Four sections: Context · Decision · Consequences · References. Status line at top. One-page max.

### `docs/adr/index.md` (per repo)
- **Why no analog:** No existing ADR index files.
- **Proposed structure:** Single-line bulleted list per ADR with `Status, Date` suffix. ~10 lines per file.

### `docs/quickstart.md` (cross-repo 30-min walkthrough)
- **Why no analog:** No existing cross-repo walkthrough doc.
- **Proposed structure:** RESEARCH §"Ops Docs Scope" lines 344-407 ships the verbatim 10-section structure + command sequence.

### CHANGELOG.md (Keep-a-Changelog-lite for photophore + seamount)
- **Why no analog:** Only thermocline has a CHANGELOG today; that one follows a different (in-progress narrative) format.
- **Proposed structure:** RESEARCH §"Release Script + CHANGELOGs" lines 855-884 ships the verbatim template (Added / Implemented / Deferred / Known limitations).

---

## Cross-file invariants

The planner MUST propagate these conventions across the relevant file groups:

1. **AT-* filename convention:** `test_at_<letter><number>_<one_word_failure>.py` for every Group A file. Lowercase letter; numeric only after the letter; one underscore separates surface ID from failure descriptor. The `at_coverage.py` filename-scan regex `^test_at_[acer](\d+)_` depends on this exactly.

2. **AT-* docstring opening:** Every Group A file's module docstring opens with `AT-X<n>: <one-line failure mode from spec README>`. The `at_coverage.py` may grow to enforce this in a future iteration.

3. **AT-* pytest marker:** Every Group A test function has `@pytest.mark.at_surface("AT-X<n>")` per CONTEXT D-01 Claude's-discretion. Register the marker in each repo's `pytest.ini` or `pyproject.toml` `[tool.pytest.ini_options].markers`.

4. **Property test top-of-file comment:** Every Group B file gets `# CONF-03 invariant: <name>` as the first non-shebang line of the module (above imports). The `property_coverage.py` tool greps for this exact prefix.

5. **`@settings(max_examples=N)` floor:** Every property test in Group B has `N >= 200`. `property_coverage.py` AST-walks `@settings` calls; any literal below 200 fails CI.

6. **MANIFEST.yaml `phase_wired:` field:** Every fixture in Group N's MANIFEST edit has `phase_wired: 4` (or `2` for backfilled fixtures). The Phase 3 AT-A1 entry uses `phase_wired: 3` — pattern is "the phase that wires the surface into a real test", not "the phase that created the fixture".

7. **ADR numbering:** Per-repo monotonic from `0001`. Thermocline reaches `0005`; photophore reaches `0002`; seamount has none. Cross-repo references use `../<repo>/docs/adr/ADR-XXXX-name.md` (no symlinks per D-03).

8. **MADR-lite section ordering:** `## Context` → `## Decision` → `## Consequences` → `## References`. Status line at top: `**Status:** Accepted · <date>`. One-page max.

9. **CHANGELOG section ordering:** Per repo, newest-on-top per Keep-a-Changelog. Sections within a release: `### Added` → `### Implemented` → `### Deferred to subsequent milestones` → `### Known limitations`. Thermocline has two new headings (`## [0.3.1]` + `## [0.1.0]`) — 0.3.1 above 0.1.0 since spec patches landed in the same release window.

10. **CLI subcommand decorator order:** `@<group>.command(...)` outermost → `@audit_cli_invocation("<name>")` → `@click.option(...)` (any number) → `@click.pass_context` innermost (per Pitfall 6 + verified click convention). Apply to every leaf command in `audit_cmds.py`, `channel_cmds.py`, `classify_cmds.py`, `policy_cmds.py`, `dispatch_cmds.py`.

11. **CI step ordering:** Structural/lint gates BEFORE pytest in every workflow. Order: `ruff` → `mypy --strict` → `pip-audit` → network-isolation lint → `print(` lint → canonical-JSON lint (thermocline) → `at_coverage.py` → `at_coverage_total.py` (thermocline) → `property_coverage.py` (thermocline) → `pytest` → `forge_conformance` (seamount/photophore-integration).

12. **`Sensitive[T]` bytes-only:** Per Pitfall 7 — keep `Sensitive[bytes]`. Do NOT introduce `Sensitive[dict]` or `Sensitive[str]` in the Group G retrofit. Field-level decisions are itemized in RESEARCH §"Sensitive[T] Sweep" table.

13. **`print(` allow-list:** Three identical `ast_lint_no_print.py` files share the same `ALLOWED_FRAGMENTS` and `ALLOWED_FORGE_FRAGMENTS`. Any drift = false positives in CI. Tests should pass on first run because RESEARCH already enumerated all 5 existing `print(` call sites.

14. **Tag message:** `git tag -a v0.1.0 -m "v0.1.0 — coordinated with thermocline v0.1.0 + photophore v0.1.0 + seamount v0.1.0"` — identical message in all three repos so `git tag -v v0.1.0` shows the coordination.

15. **`tools/` directory bootstrapping:** `seamount/tools/` and `thermocline/tools/` do not exist today. Plan 04-01 first task must create them. `photophore/tools/` exists (verified — contains `ast_lint_network_isolation.py`).

---

## PATTERN MAPPING COMPLETE

**Files mapped:** 56 (43 new, 13 modify) across thermocline + photophore + seamount.
**Strong analogs found:** 43 / 56 — every new test, source edit, lint tool, and AT-* fixture has a verified in-tree pattern to mirror.
**New-shape files:** 13 — `at_coverage_total.py`, `property_coverage.py`, `tag-v0.1.0.sh`, 7 ADR files, 3 ADR index files, `quickstart.md`, 2 new CHANGELOGs. RESEARCH already ships verbatim templates for all of these.
**Cross-file invariants:** 15 conventions the planner must propagate (filename patterns, decorator orders, CI step orders, etc.).
**Critical pre-plan verifications carried forward from RESEARCH:**
  1. Fixture filename ↔ surface ID reconciliation (Pitfall 3 / Open Question 1)
  2. `mypy --strict` probe on seamount forges (Open Question 2 / CONFLICT-04)
  3. `photophore audit archive` command existence (Open Question 3 / Assumption A4)
  4. Click decorator stacking with `@audit_cli_invocation` (Assumption A8)
**Ready for planning:** Yes. Every file in CONTEXT.md's work-distribution sketch has a concrete `<read_first>` analog the planner can paste into task action blocks.
