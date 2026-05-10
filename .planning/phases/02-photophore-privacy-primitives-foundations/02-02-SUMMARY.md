---
phase: "02"
plan: "02"
subsystem: "photophore"
tags: ["classifier", "privacy", "cli", "hypothesis", "pathspec", "conformance", "CLASS-01", "CLASS-02", "CLASS-03", "CLASS-04", "CLASS-05", "CLASS-06", "CLI-04"]
dependency_graph:
  requires:
    - "02-01: photophore package scaffold + Tier enum (photophore.core) + PhotophoreError base (photophore.errors)"
  provides:
    - "photophore.classifier: classify(), default_tier(), load_rules(), Classification, Reason, PathRule, PathRules"
    - "CLASS-01 priority order: Explicit Tag > Path Rule > Rule-based Classifier > Default"
    - "CLASS-06 default_tier() named function with Hypothesis property test (>=100 cases)"
    - "photophore classify CLI subcommand (CLI-04) with D-12 output modes and D-14 exit codes"
    - "AT-A3 conformance fixture in conformance/valid/ (W12: documents intended behavior)"
  affects:
    - "02-03: shadow/policy can gate on classify() at dispatch time"
    - "Phase 3 dispatch coordinator: classify per ContentBlock in 9-step flow (DISP-01)"
tech_stack:
  added:
    - "pathspec>=1.1.1 (gitwildmatch-compatible gitignore pattern matching; already in pyproject.toml from 02-01)"
    - "types-PyYAML (mypy stubs for pyyaml; installed in dev environment)"
  patterns:
    - "typing.Protocol with @property for read-only frozen dataclass compatibility (W7 — no type:ignore)"
    - "pathspec 'gitignore' pattern name (successor to deprecated 'gitwildmatch'; same semantics)"
    - "Hypothesis @given + @settings(max_examples=100, deadline=None) for CLASS-06 invariant"
    - "Real-fixture-from-disk discipline: all test YAML loaded from tests/fixtures/ (BL-04)"
key_files:
  created:
    - "photophore/python/src/photophore/classifier/__init__.py"
    - "photophore/python/src/photophore/classifier/_types.py"
    - "photophore/python/src/photophore/classifier/_tags.py"
    - "photophore/python/src/photophore/classifier/_default.py"
    - "photophore/python/src/photophore/classifier/_rules.py"
    - "photophore/python/src/photophore/classifier/_engine.py"
    - "photophore/python/src/photophore/classifier/_patterns.py"
    - "photophore/python/src/photophore/cli/classify_cmds.py"
    - "photophore/python/tests/test_classifier_tags.py"
    - "photophore/python/tests/test_classifier_rules.py"
    - "photophore/python/tests/test_classifier_engine.py"
    - "photophore/python/tests/test_classifier_priority.py"
    - "photophore/python/tests/test_classifier_default_property.py"
    - "photophore/python/tests/test_cli_classify.py"
    - "photophore/python/tests/fixtures/rules-valid.yaml"
    - "photophore/python/tests/fixtures/rules-no-catchall.yaml"
    - "photophore/python/tests/fixtures/rules-malformed.yaml"
    - "thermocline/conformance/valid/AT-A3-priority-order-explicit-tag.json"
  modified:
    - "photophore/python/src/photophore/errors.py (appended RulesConfigError + ClassifierError)"
    - "photophore/python/src/photophore/cli/_errors.py (appended ClassifierError exit_code=4)"
    - "photophore/python/src/photophore/cli/__init__.py (wired classify_cmd)"
    - "thermocline/conformance/valid/MANIFEST.yaml (added fixtures: section + AT-A3 entry)"
decisions:
  - "W7 ADOPTED: PathRules defined as typing.Protocol with @property for rules, enabling frozen dataclass _LoadedPathRules to satisfy it without type:ignore[return-value]"
  - "pathspec 'gitignore' pattern used instead of deprecated 'gitwildmatch' name (same gitwildmatch semantics, no breaking change)"
  - "credential_env_assignment regex widened to [\\x21-\\x7E] to match URLs with @ (postgres://user:pass@host)"
  - "W12 ADOPTED: AT-A3 fixture lives in conformance/valid/ — documents intended CLASS-01 priority behavior, not a violation"
  - "photophore classify uses @click.command (not @click.group) since no subcommands exist; group structure deferred until needed"
metrics:
  duration: "~53 minutes"
  completed: "2026-05-10"
  tasks_completed: 4
  files_created: 18
  files_modified: 4
  tests_written: 86
  hypothesis_examples: 200
---

# Phase 2 Plan 2: Classifier Module + CLI Subcommand Summary

**One-liner:** Photophore classifier module with strict 4-priority branch order (CLASS-01), default_tier() named function pinned by 200 Hypothesis examples, v0.1 credential/PII/file-extension patterns, pathspec gitwildmatch path-rule matching, and `photophore classify` CLI with D-12/D-14 compliance.

## Confirmed Public API Surface

```python
from photophore.classifier import (
    classify,           # classify(content, path=None, rules=None) -> Classification
    default_tier,       # CLASS-06 named function returning Tier.LOCAL
    load_rules,         # load_rules(path) -> PathRules (raises RulesConfigError at load time)
    parse_explicit_tag, # parse_explicit_tag(content: bytes) -> Tier | None
    Classification,     # frozen dataclass: tier + reason
    Reason,             # Enum: EXPLICIT_TAG / PATH_RULE / CLASSIFIER_RULE / CLASSIFIER_DEFAULT
    PathRule,           # frozen dataclass: pattern + tier + reason
    PathRules,          # typing.Protocol: rules property + match(path) method
)

from photophore.errors import RulesConfigError, ClassifierError
```

## CLASS-01 Priority Order — Exact Test File References

| Priority | Branch | Test File | Key Test |
|----------|--------|-----------|----------|
| 1 | Explicit Tag (CLASS-02) | test_classifier_priority.py | test_at_a3_explicit_tag_wins_over_path_rule |
| 2 | Path Rule (CLASS-03) | test_classifier_priority.py | test_at_a3_without_tag_path_rule_applies |
| 3 | Rule-based Classifier (CLASS-04) | test_classifier_priority.py | test_priority_3_fires_without_path_rule |
| 4 | Default (CLASS-06) | test_classifier_default_property.py | test_innocuous_content_hits_default_branch |

Full priority order pinned in `test_classifier_priority.py::test_all_four_priorities_verified`.

## CLASS-06 Named-Function Gate

Acceptance criterion enforced in `test_classifier_engine.py::test_engine_has_no_tier_local_literals`:
- Reads `_engine.py` source and asserts `"Tier.LOCAL" not in engine_src`
- Enforces that the default branch calls `default_tier()` (the named function), never a literal

Hypothesis property tests (200 examples total):
- `test_unmatched_content_classifies_as_local`: `@given(binary(0..10_000))` — any content without explicit tag -> LOCAL
- `test_innocuous_content_hits_default_branch`: `@given(text(alphabet="abc ").map(encode))` — guaranteed no credential/PII hit -> `classifier:default`

## pathspec Dependency Rationale

From 02-RESEARCH.md key finding #2: `fnmatch` and `pathlib.PurePath.match` both fail on `**/.env*` matching bare `.env`. `pathspec>=1.1.1` with gitwildmatch semantics passes this test. Confirmed by `test_pathspec_matches_bare_dotenv` in `test_classifier_rules.py`.

Implementation note: the `pathspec.PathSpec.from_lines("gitignore", ...)` call uses the `gitignore` pattern name, which is the successor to the deprecated `gitwildmatch` name with identical semantics.

## yaml.safe_load Enforcement (Pitfall 5)

- `_rules.py` uses `yaml.safe_load` exclusively
- Acceptance criterion gate: `grep -RnE "yaml.load\(" src/photophore/classifier/ | grep -vE "yaml.safe_load" | wc -l` == 0
- `test_load_rules_uses_safe_load_not_load` verifies source-level compliance

## AT-A3 Fixture Framing (W12: Intended Behavior)

AT-A3 (`thermocline/conformance/valid/AT-A3-priority-order-explicit-tag.json`) documents the explicit-tag-wins priority rule from CLASS-01. This is INTENDED behavior:

- Explicit tags are issuer-authored signals on the issuer node — the trust anchor
- An attacker who can inject `@photophore:public` into content has issuer-node access (AT-A1, a separate threat)
- The fixture pins that explicit tags ALWAYS take priority AND that without a tag, content stays LOCAL
- Placed in `conformance/valid/` (not `invalid/`) to clarify this is correct behavior

Behavioral wire: `test_classifier_priority.py::test_at_a3_explicit_tag_wins_over_path_rule` and `test_at_a3_without_tag_path_rule_applies`.

## Requirement Crosswalk

| Req ID | Test File | Test Function |
|--------|-----------|---------------|
| CLASS-01 | test_classifier_priority.py | test_all_four_priorities_verified, test_priority_* |
| CLASS-02 | test_classifier_tags.py | test_parse_explicit_tag_case_insensitive |
| CLASS-03 | test_classifier_rules.py | test_load_rules_no_catchall_raises_at_load_time |
| CLASS-04 | test_classifier_rules.py | test_classify_by_rules_*, test_classify_by_rules_never_promotes_to_public |
| CLASS-05 | test_classifier_engine.py | test_classify_* (reason format assertion) |
| CLASS-06 | test_classifier_default_property.py | test_unmatched_content_classifies_as_local (100 examples), test_innocuous_content_hits_default_branch (100 examples) |
| CLI-04 | test_cli_classify.py | all 12 tests |

## Commits

| Task | Commit | Repo | Description |
|------|--------|------|-------------|
| 1 | 6dad7e6 | photophore | Classifier types + explicit-tag parser + default_tier |
| 2 | 794cd90 | photophore | Path-rules YAML loader + rule-based classifier patterns |
| 3 | 6423c71 | photophore | classify() engine + Hypothesis property tests |
| 4 | b957c5c | photophore | photophore classify CLI subcommand |
| 4 | fe2f387 | thermocline | AT-A3 conformance fixture + valid/MANIFEST.yaml |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pathspec "gitwildmatch" pattern name deprecated**
- **Found during:** Task 2 test run (DeprecationWarning on pathspec.PathSpec.from_lines)
- **Issue:** pathspec deprecated the "gitwildmatch" pattern name. Tests produced 72 DeprecationWarnings.
- **Fix:** Changed to "gitignore" pattern name, which has identical gitwildmatch semantics per pathspec docs
- **Files modified:** `photophore/python/src/photophore/classifier/_rules.py`
- **Commit:** 794cd90

**2. [Rule 1 - Bug] credential_env_assignment regex rejected URLs with @ character**
- **Found during:** Task 2 test `test_classify_by_rules_env_assignment`
- **Issue:** The char class `[A-Za-z0-9+/=:_/-]` does not include `@`, so `DATABASE_URL=postgres://user:pass@host` returned None instead of "credential_env_assignment"
- **Fix:** Widened char class to `[\x21-\x7E]` (all printable non-whitespace ASCII), which covers URL characters including `@`, `%`, `?`, etc.
- **Files modified:** `photophore/python/src/photophore/classifier/_patterns.py`
- **Commit:** 794cd90

**3. [Rule 1 - Bug] PathRules Protocol incompatible with frozen dataclass return (W7)**
- **Found during:** Task 2 mypy --strict run (error: Incompatible return value type — Protocol member PathRules.rules expected settable variable, got read-only attribute)
- **Issue:** `rules: tuple[PathRule, ...]` in a Protocol means the attribute is read-write, but `_LoadedPathRules` is a frozen dataclass where all attributes are read-only
- **Fix:** Changed `rules` in `PathRules` Protocol from a class variable to a `@property` declaration. Frozen dataclass read-only attributes satisfy read-only Protocol properties
- **Files modified:** `photophore/python/src/photophore/classifier/_types.py`
- **Commit:** 794cd90

**4. [Rule 1 - Bug] _engine.py docstring contained "Tier.LOCAL" literal, failing acceptance criterion**
- **Found during:** Task 3 test `test_engine_has_no_tier_local_literals`
- **Issue:** The acceptance criterion (`grep "Tier.LOCAL" _engine.py | wc -l == 0`) is enforced by source grep. The docstring contained "Tier.LOCAL" in comments/docstring.
- **Fix:** Replaced "Tier.LOCAL" references in docstring and comments with "local" (lowercase) prose descriptions
- **Files modified:** `photophore/python/src/photophore/classifier/_engine.py`
- **Commit:** 6423c71

**5. [Rule 1 - Bug] test_parse_explicit_tag_case_insensitive expected @PHOTOPHORE to return None**
- **Found during:** Task 1 test run
- **Issue:** The test initially expected `@PHOTOPHORE:public` to return None (only tier name case-insensitive), but the regex uses `re.IGNORECASE` for the whole pattern per CLASS-02 "case-insensitive" spec.
- **Fix:** Updated test to expect `Tier.PUBLIC` for `@PHOTOPHORE:public` — the spec is case-insensitive for the whole tag
- **Files modified:** `photophore/python/tests/test_classifier_tags.py`
- **Commit:** 6dad7e6

## Known Stubs

None. All public API methods are fully implemented. The classifier v0.1 patterns are intentionally limited (9 patterns + 12 extensions); v0.3 extension with model-backed detection is documented as out of scope.

## Threat Flags

No new threat surfaces introduced beyond those documented in the plan's `<threat_model>`. All STRIDE threats (T-02-14 through T-02-23) are mitigated as specified.

## Self-Check

### Files Exist

- photophore/python/src/photophore/classifier/__init__.py: FOUND
- photophore/python/src/photophore/classifier/_types.py: FOUND
- photophore/python/src/photophore/classifier/_tags.py: FOUND
- photophore/python/src/photophore/classifier/_default.py: FOUND
- photophore/python/src/photophore/classifier/_rules.py: FOUND
- photophore/python/src/photophore/classifier/_engine.py: FOUND
- photophore/python/src/photophore/classifier/_patterns.py: FOUND
- photophore/python/src/photophore/cli/classify_cmds.py: FOUND
- photophore/python/tests/fixtures/rules-valid.yaml: FOUND
- photophore/python/tests/fixtures/rules-no-catchall.yaml: FOUND
- photophore/python/tests/fixtures/rules-malformed.yaml: FOUND
- thermocline/conformance/valid/AT-A3-priority-order-explicit-tag.json: FOUND
- thermocline/conformance/valid/MANIFEST.yaml (updated): FOUND

### Commits Exist

- 6dad7e6 (photophore): Task 1 — classifier types + explicit-tag parser + default_tier
- 794cd90 (photophore): Task 2 — path-rules YAML loader + rule-based classifier patterns
- 6423c71 (photophore): Task 3 — classify() engine + Hypothesis property tests
- b957c5c (photophore): Task 4 — photophore classify CLI subcommand
- fe2f387 (thermocline): Task 4 — AT-A3 conformance fixture + valid/MANIFEST.yaml

### Test Counts

- test_classifier_tags.py: 26 tests
- test_classifier_rules.py: 25 tests
- test_classifier_engine.py: 14 tests
- test_classifier_priority.py: 7 tests
- test_classifier_default_property.py: 2 tests (200 Hypothesis examples)
- test_cli_classify.py: 12 tests

Total: 86 new tests + 81 pre-existing tests = 167 passing

### mypy --strict

0 errors on 13 source files (7 classifier + 6 CLI)

## Self-Check: PASSED
