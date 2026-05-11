---
phase: 2
phase_name: "photophore-privacy-primitives-foundations"
project: "Thermocline Suite"
generated: "2026-05-10"
counts:
  decisions: 13
  lessons: 11
  patterns: 12
  surprises: 10
missing_artifacts:
  - "02-VERIFICATION.md"
  - "02-UAT.md"
---

# Phase 2 Learnings: photophore-privacy-primitives-foundations

## Decisions

### D-01..D-03 — Audit log = single denormalized table + JSON1 payload + chain hash over canonical(entry minus entry_hash)
One `entries` table with indexed metadata columns (`id`, `algo_version`, `prev_hash`, `entry_hash`, `event_type`, `channel_id` NULLABLE, `envelope_id` NULLABLE, `timestamp`) plus a `payload TEXT` column holding canonical-JSON of event-specific fields. Spec-mandated AUDIT-05 filters (channel/node/tier/date/shadow_id/envelope_id) ride indexed columns + a small set of JSON1 expressions. `entry_hash = blake3(canonicalize(entry minus entry_hash))`; `algo_version="blake3-v1"` encodes hash fn AND domain rule from day 1.

**Rationale:** Single-table walk for AT-A4 chain-integrity verification is the simplest verifier loop; export to JSON Lines is `SELECT * + payload concat`; SQLite triggers (BEFORE DELETE / BEFORE UPDATE RAISE ABORT) enforce append-only AUDIT-01 on one table. Whole-entry domain reuses Phase 1's `canonicalize` with no new code path; a future `blake3-v2` may change either fn or domain — verifier dispatches on `algo_version` from day 1 per AUDIT-02.
**Source:** 02-CONTEXT.md (D-01..D-03), 02-01-SUMMARY.md

---

### D-04..D-07 — Three discrete stores, three files; keystore-as-truth; three-step atomic write ordering
Trust store = `python-keyring` (service `photophore.channel`, username = channel_id, value = canonical-JSON of record). Metadata index = a separate SQLite `channels.db`. Audit log = its own `audit.db`. Three discrete stores, three files. Bootstrap walks keystore → compares against index → rebuilds index from keystore on any drift; an unaudited channel (in keystore but no `channel.created` event) hard-halts the node. Channel ops use exactly this order: (1) `keystore.set` (incl. `_index` sentinel update), (2) `audit.append`, (3) `channels.db.upsert`. CLI returns success only after step 3.

**Rationale:** CHAN-04 / AT-A5 satisfied to the letter — different stores AND different files (the audit log can never co-locate with the trust store via shared filesystem). Keystore-first ordering reflects "trust store is authoritative"; index-as-derived means index rebuild is always safe; halt-on-mismatch surfaces real damage instead of papering over it. Single audit entry per channel op = cleaner log.
**Source:** 02-CONTEXT.md (D-04..D-07), 02-01-SUMMARY.md

---

### D-08..D-10 — Path-rules: YAML, load-per-invocation, mandatory `**`→`local` catch-all enforced at load time
Rules config is YAML at `~/.config/photophore/rules.yaml` (or `$XDG_CONFIG_HOME/photophore/rules.yaml`); CLI `--rules` flag overrides for testing/preview. No CWD-walking, no per-project config in v0.1. Ordered list of `{pattern: glob, tier: local|shared|public, reason: str}` with first-match-wins. The final entry MUST be `{pattern: "**", tier: local, reason: "default"}` — missing it raises `RulesConfigError` at `load_rules()` time, before any classify call returns. Operations not requiring classification (`channel`, `audit query/export/verify`) do not load the file.

**Rationale:** Runtime fallthrough would silently classify unmatched content as something other than `local` — exactly the false-positive mode the spec forbids. YAML aligns with Phase 1 D-04 conformance manifest format. Sovereign-node-per-user is the v0.1 mental model; per-project config can revisit if v0.2+ adds the use case.
**Source:** 02-CONTEXT.md (D-08..D-10), 02-02-SUMMARY.md

---

### D-11 — Sync Phase 2 + thin async shim in Phase 3 only
All Phase 2 public APIs are sync `def`: `audit.append/query/export/verify`, `channels.create/list/show/transition/set_ceiling`, `classify(content)`, `shadow.generate(...)`, `policy.author(...)`. SQLite via stdlib `sqlite3` (no `aiosqlite`). Zero `async def` anywhere in Phase 2. Phase 3 will ship a small `photophore.dispatch.aio` shim (~20 LOC) using `asyncio.to_thread`.

**Rationale:** Pure-CPU functions (classifier, shadow) shouldn't be `async def`. Sync core keeps domain logic readable, testable, dependency-light. Phase 3 dispatch is the only async surface and owns its own boundary code. Enforced from day 1 via grep gates co-located with `test_shadow_no_caching.py` (`no async def`, `no aiosqlite import` lines).
**Source:** 02-CONTEXT.md (D-11), 02-03-SUMMARY.md

---

### D-12..D-14 — CLI conventions: --json with JSONL-twist for streaming subcommands; click groups under single `photophore` binary; structured exit codes 0–5
Single binary `photophore` exposed via `[project.scripts]`, with `click.Group` per area: `channel|audit|classify|policy <subcmd>`. `--json` everywhere; `audit query|export` emit JSON Lines (one entry per line, streaming-friendly), all others emit a single JSON document. Exit codes: 0 success, 1 generic, 2 config, 3 audit-chain integrity failure, 4 classifier error, 5 keystore error (Phase 3 reserves 6 for dispatch errors).

**Rationale:** Per-subcommand JSON-vs-JSONL distinction is by nature (streaming vs document); no `--format=` enum needed. Predictable exit codes make CI integration trivial; audit-chain failure (3) is distinct from generic error (1) because it signals a privacy-critical incident requiring forensic followup. CONF-07 ops docs will reference these directly.
**Source:** 02-CONTEXT.md (D-12..D-14), 02-01-SUMMARY.md

---

### OQ-1 — `_index` sentinel at `photophore.channel:_index` because python-keyring has no enumerate API
`python-keyring` exposes `set_password/get_password/delete_password` but no `list_passwords_for_service()`. The keystore-as-truth bootstrap in D-05 cannot work without enumeration. Resolution: store a JSON array of channel_ids under service `photophore.channel`, username `_index`; update it atomically inside step 1 of the D-07 write order; bootstrap walks `_index` to compare against `channels.db`.

**Rationale:** Without `_index` we cannot detect "record exists in keystore but missing from index" — the exact AT-A5-adjacent drift mode D-05 requires we hard-halt on. The sentinel is the smallest possible primitive that makes the trust-store authoritative.
**Source:** 02-01-SUMMARY.md

---

### OQ-2 — `_ResultPolicy` renamed public as `ResultPolicy` in thermocline-py (cross-impl spec patch)
Phase 1 shipped `ResultPolicy` as private (`_ResultPolicy`) because no caller existed. Plan 02-03's `policy.author()` needs to return one as part of the public API contract; Phase 3 dispatch coordinator imports it. Resolution: rename in `thermocline.envelope`, add to `__all__`, regenerate the 5 schema artifacts (`$defs` key flipped in `task.schema.json` and `job.schema.json`), record in `thermocline/CHANGELOG.md` v0.3.1 as a cross-implementation contract event, retain backward-compat alias `_ResultPolicy = ResultPolicy`.

**Rationale:** Same pattern as Phase 1 THERMO-01 (cirdan→thermocline rename) — when implementation discovers a privacy primitive's surface needs widening, the spec moves, not the implementation. Schema regeneration is mandatory (D-02 drift gate); the CHANGELOG entry is the cross-impl contract record for Rust/TypeScript ports.
**Source:** 02-03-SUMMARY.md

---

### OQ-3 — Shadow API split: hard-fail raises, soft-fail returns warnings
`ShadowResult(shadow: Shadow, warnings: tuple[str, ...])` frozen dataclass. Irreversibility failures raise `ShadowIrreversibilityError` (dispatch must abort). Relevance and distinguishability failures populate `warnings`; dispatch records non-empty warnings to audit and proceeds.

**Rationale:** SHADOW-04 spec mandates "irreversibility is hard, the other two are soft" — encoding the split in two different mechanisms (exception vs collected list) makes "did dispatch correctly handle the soft case?" trivially auditable. A single warnings list that also includes the hard-fail string would let a buggy dispatch swallow the irreversibility violation.
**Source:** 02-03-SUMMARY.md

---

### `_IRREVERSIBILITY_MIN_SUBSTR_LEN = 8` (not 4)
Named constant enforcing the minimum-substring length the irreversibility test searches for in source content. Lifted from 4 to 8 after empirical false-positives.

**Rationale:** A 4-char threshold matches common English bigram-pairs ("at", "of", "in") and short variable names — every plaintext "the cat" trips the gate. 8 chars eliminates that class of false positive while still catching real leakage of identifiers, fragments of credentials, code substrings. Documented in research §7.
**Source:** 02-03-SUMMARY.md

---

### Closed enum + match for ContentType abstraction (not registry pattern)
`ContentType` is a closed 6-member enum (`DOCUMENT`, `CONVERSATION`, `CREDENTIAL`, `FILE`, `IDENTITY`, `CODE`); `_generate_abstraction()` is a `match content_type:` statement with exactly 6 arms. Adding a 7th type in v0.2 is "add enum member + add match arm" — two localized changes.

**Rationale:** Registry pattern was the alternative — open-ended, easier to add types to. But v0.1 ships the spec-mandated 6 and the closed-set guarantees `mypy --strict` exhaustiveness checking via `case _ as never` fallthrough. v0.2 extension cost is small enough that the type-safety win is unambiguous.
**Source:** 02-CONTEXT.md (planner discretion section), 02-03-SUMMARY.md

---

### Credential-abstraction vocabulary uses "auth-secret of class X" (not "credential of type X")
Abstraction labels emitted by `_abstract_credential()` avoid the literal word "credential" because source content classified as `CREDENTIAL` is overwhelmingly likely to contain that word too.

**Rationale:** "credential of type generic" (vocabulary candidate A) shares the 8-char substring "credenti" with source content `b"credential content"`, tripping the irreversibility test as a false positive. Semantic substitution ("auth-secret of class pem-encoded-key") preserves spec intent (label conveys the kind only) without word-overlap. Establishes a general rule: shadow labels must avoid vocabulary highly correlated with their source content type.
**Source:** 02-03-SUMMARY.md

---

### W7 — `PathRules` Protocol uses `@property` to be satisfiable by a frozen dataclass
The `PathRules` Protocol exposes `rules: tuple[PathRule, ...]` and `match(path)`. Initially typed as a class variable, which mypy treats as read-write — frozen dataclasses cannot satisfy that. Resolution: `@property def rules(self) -> tuple[PathRule, ...]: ...` in the Protocol; frozen dataclass auto-generated read-only attribute satisfies it without any `# type: ignore`.

**Rationale:** Phase 1 BL-02 lesson "explicit casts over `# type: ignore`" applies. `@property` on the Protocol surface is the structurally correct way to declare read-only-shape intent.
**Source:** 02-02-SUMMARY.md

---

### W12 — AT-A3 fixture lives in `conformance/valid/`, documenting intended CLASS-01 priority behavior
AT-A3 (explicit-tag-wins-over-path-rule) initially proposed for `invalid/`. Resolution: this is intended priority behavior, not a threat-model violation; explicit tags are issuer-authored signals on the issuer node — they are the trust anchor. An attacker injecting `@photophore:public` would already have issuer-node access (covered by AT-A1, a separate surface). Fixture in `conformance/valid/` makes the framing unambiguous to cross-language ports.

**Rationale:** Phase 1 D-04 conformance taxonomy (valid = "behavior the suite must exhibit"; invalid = "behavior the suite must reject") only stays useful if fixtures are categorized strictly. Mis-filing AT-A3 in `invalid/` would have implied issuer-tag priority was a bug class rather than the design.
**Source:** 02-02-SUMMARY.md

---

## Lessons

### `python-keyring` has no `list_passwords_for_service()` API
The library exposes per-(service, username) `set`/`get`/`delete` and nothing else. Any enumeration must be implemented above the library — a `_index` sentinel record under a known username is the canonical workaround. There is no platform-specific backend that adds enumeration; this is a library-wide constraint.

**Context:** Discovered during 02-RESEARCH for D-05 keystore-as-truth bootstrap. The constraint is invisible from the library's API docs until you go looking for it. Generalizes: any storage layer that exposes only point lookups requires an index sentinel for keystore-as-truth patterns.
**Source:** 02-RESEARCH.md, 02-01-SUMMARY.md (OQ-1)

---

### SQLite millisecond-resolution timestamps + UUIDv4 row IDs don't preserve insertion order
`AuditLog._last_entry_hash()` initially used `ORDER BY timestamp DESC, id DESC LIMIT 1`. Multiple entries landing in the same millisecond shared a timestamp, and UUIDv4-based `id` ordering is not insertion-order. The third entry's `prev_hash` would point at the second entry's hash sometimes — and at the first entry's hash other times.

**Context:** Caught by Plan 02-01 Task 1 test `test_third_entry_prev_hash_equals_second_entry_hash`. Fix: `ORDER BY rowid DESC LIMIT 1`. SQLite's `rowid` is monotonic within a connection and is the only reliable insertion-order signal when timestamps collide.
**Source:** 02-01-SUMMARY.md

---

### Hypothesis `@given(...) + assume(...)` exhausts the search budget before reaching `max_examples`
`@given(n_entries=integers(2..10), tamper_index=integers(0..9))` plus `assume(tamper_index < n_entries)` rejected ~40% of cases. Hypothesis exhausted the budget at 54 valid examples instead of 100.

**Context:** Plan 02-01 Task 1 chain-tamper property test. Fix: `flatmap` to generate correlated pairs: `st.integers(2..15).flatmap(lambda n: st.integers(0..n-1).map(lambda i: (n, i)))`. 100% valid examples; no `assume()` needed. Generalizes: any "draw `i < n`" property test should use `flatmap`, not `assume`.
**Source:** 02-01-SUMMARY.md

---

### `pathspec`'s "gitwildmatch" pattern name is deprecated; "gitignore" is the documented alias
`pathspec.PathSpec.from_lines("gitwildmatch", ...)` emits a DeprecationWarning per call. 72 warnings surfaced in Plan 02-02 Task 2 tests. "gitignore" is the supported successor name; semantics are identical.

**Context:** Plan 02-02 selected pathspec for `**/.env*`→`.env` glob matching (which `fnmatch` and `pathlib.PurePath.match` both fail on). The library-version observation didn't surface in research; the executor caught it from test output.
**Source:** 02-02-SUMMARY.md, 02-RESEARCH.md (§6)

---

### Source-grep acceptance tests trip on prose mentions of the forbidden token
`test_engine_has_no_tier_local_literals` asserts `"Tier.LOCAL" not in engine_src`. The docstring at the top of `_engine.py` originally said "the default branch returns `Tier.LOCAL`". The gate fired on the docstring, not on a real literal.

**Context:** Plan 02-02 Task 3. Fix: replace the docstring's `Tier.LOCAL` with lowercase prose "the default branch returns local". Same lesson recurred in Plan 02-03 for the SHADOW-06 no-caching grep gate (`@lru_cache` matched documentation mentions of the prohibition). General fix: anchor source-grep patterns to syntactic shapes (`^\s*@lru_cache`, `^\s*_shadow_cache\s*=`) that prose cannot satisfy.
**Source:** 02-02-SUMMARY.md, 02-03-SUMMARY.md

---

### `credential_env_assignment` regex char-class must include URL-shape characters
The first version of the rule-based credential pattern used `[A-Za-z0-9+/=:_/-]` — covered Base64, hex, and Unix paths. `DATABASE_URL=postgres://user:pass@host` returned None because `@`, `?`, `%` weren't in the class. Widened to `[\x21-\x7E]` (all printable non-whitespace ASCII).

**Context:** Plan 02-02 Task 2 test `test_classify_by_rules_env_assignment`. Lesson: regex char-classes for "credential-shaped value" should err on permissive — false-negatives are acceptable (per CLAUDE.md classifier asymmetry), but only after we've enumerated common real shapes.
**Source:** 02-02-SUMMARY.md

---

### Shadow abstraction vocabulary that overlaps source content trips the irreversibility test as a false positive
`_abstract_credential()` returned "credential of type generic"; source content `b"credential content"` contains the 8-char substring "credenti" too. The irreversibility check correctly flags the substring overlap — but the cause is the abstraction's word choice, not real leakage.

**Context:** Plan 02-03 Task 2. Fix: rewrite abstraction vocabulary to use semantic substitutes ("auth-secret of class X"). Establishes a general rule: shadow labels for content type X must avoid vocabulary highly correlated with content of type X. This is asymmetric to the lesson above — for the classifier we want permissive regex (catch more); for the shadow generator we want narrow vocabulary (avoid overlap).
**Source:** 02-03-SUMMARY.md

---

### `_IRREVERSIBILITY_MIN_SUBSTR_LEN = 4` matches common English bigram-pairs
A 4-character threshold for "shadow abstraction must not contain any substring this long from the source" produces false positives on the most common English words ("at", "of", "in") and short variable names. 8 chars is the empirical clean threshold.

**Context:** 02-RESEARCH §7 + Plan 02-03 Task 2 corpus testing. Lesson generalizes: irreversibility thresholds (and any "n-gram leakage" guards) should be tuned empirically against a realistic corpus, not picked from a security textbook. The corpus needs to include both target classes (credentials, code, identity strings) and innocuous English prose.
**Source:** 02-03-SUMMARY.md

---

### `click.testing.CliRunner` interleaves stderr error lines into `result.output`
The audit-chain-broken CLI test parsed `result.output` as a single JSON document — and failed because click had appended `Error: chain integrity violation at entry N` after the JSON. CliRunner's `mix_stderr=True` (the default) concatenates stderr after stdout. Fix: filter "Error: " lines from `result.output` before `json.loads`, OR pass `mix_stderr=False` to the runner.

**Context:** Plan 02-01 Task 3. The behavior is documented in click but easy to miss; tests that assert `json.loads(result.output)` need to be defensive. Generalizes: any CLI test that runs a non-success path AND asserts on JSON output must split stdout/stderr explicitly.
**Source:** 02-01-SUMMARY.md

---

### Thermocline editable install (`.pth`) can point to a stale worktree path
Plan 02-01 Task 1's `from thermocline import canonicalize` failed because `_editable_impl_thermocline.pth` resolved to `/.claude/worktrees/agent-*/...` from a prior session. The worktree had been cleaned up; the path no longer existed. Fix: `pip install -e /Users/dom/Projects/dom/thermocline/thermocline/python/` to repoint the editable install at canonical source.

**Context:** Phase 1 ran most executors inside worktrees that were later deleted. The system-level Python env retained stale references. Lesson generalizes: after worktree cleanup, any editable install pointing at the worktree must be reinstalled from the canonical source.
**Source:** 02-01-SUMMARY.md

---

### `types-PyYAML` is required for `mypy --strict` to type-check `yaml.safe_load` usage
`yaml.safe_load` returns `Any` to mypy without stubs; with stubs it returns a properly-typed union of YAML scalar types. `types-PyYAML` ships as a separate dev dependency (PEP 561 stub-only package).

**Context:** Plan 02-02 Task 2 mypy run. Lesson: any third-party library accessed inside `--strict` Python code needs to be checked for an accompanying `types-*` stub package. The pattern recurs across `types-requests`, `types-PyYAML`, `types-click`, etc.
**Source:** 02-02-SUMMARY.md

---

## Patterns

### `_index` sentinel for keystore-enumeration on backends without list-by-service API
A reserved username (`_index`) under the same service holds a JSON array of all real usernames. Mutations to real entries update the index atomically in the same critical section. Bootstrap walks the index to enumerate.

**When to use:** Any storage layer that exposes only point lookups (`set/get/delete`) but whose consumer needs enumeration. The pattern generalizes beyond `python-keyring` to any KV store without a list operation.
**Source:** 02-01-SUMMARY.md (OQ-1)

---

### D-07 three-step write ordering for atomic cross-store operations
For an op that must update keystore + audit log + index in one logical commit, write in this order: (1) keystore (incl. `_index` update), (2) audit append, (3) index upsert. Failure between steps surfaces at startup as a hard-halt (keystore-vs-audit drift → unaudited channel detected) OR is repaired automatically (keystore-vs-index drift → rebuild index from keystore).

**When to use:** Any cross-store write where one store is the trust anchor, one is the witness, and one is a derived projection. The trust anchor writes first; the witness writes second; the projection writes last. Index-as-derived is the recovery path.
**Source:** 02-CONTEXT.md (D-07), 02-01-SUMMARY.md

---

### Whole-entry canonical-JSON as chain hash domain (vs header-only domain)
`entry_hash = blake3(canonicalize(entry_dict_with_entry_hash_removed))`. The `algo_version` field encodes both the hash function AND the domain rule from day 1. A future `algo_version="blake3-v2"` may change either or both; the verifier dispatches on `algo_version` per AUDIT-02.

**When to use:** Any chained-record system whose primary read pattern is full-entry walk (for verification) and where forward archival/redaction is not a v0.1 requirement. Header-only domain becomes preferable if redaction-while-preserving-chain becomes a requirement; the `algo_version` field is the migration lever.
**Source:** 02-CONTEXT.md (D-03), 02-01-SUMMARY.md

---

### Hypothesis `flatmap` for correlated integer ranges (no `assume` rejections)
`st.integers(min_value=2, max_value=N).flatmap(lambda n: st.integers(0, n-1).map(lambda i: (n, i)))` generates `(n_entries, tamper_index)` pairs with 100% validity. No `assume(i < n)`; no search-budget exhaustion.

**When to use:** Any property test where one input's valid range depends on another input's value. `flatmap` is structurally correct; `assume` is a budget tax that can fail to reach `max_examples`.
**Source:** 02-01-SUMMARY.md

---

### Closed enum + `match` statement for spec-mandated content-type dispatch
A closed enum (`ContentType` with 6 members) dispatched via `match content_type:` with one arm per member plus a `case _ as never` fallthrough exhaustiveness gate. `mypy --strict` enforces exhaustiveness. v0.2 extension = add enum member + add match arm (two localized changes).

**When to use:** Spec-mandated closed sets where exhaustiveness is part of the safety property and extensions are spec-version-gated (not user-registered). For user-registered extensions, prefer a registry pattern.
**Source:** 02-CONTEXT.md (Claude's Discretion), 02-03-SUMMARY.md

---

### Frozen result dataclass with hard-fail-raises / soft-fail-warnings-tuple split
`ShadowResult(shadow: Shadow, warnings: tuple[str, ...])` frozen dataclass. Hard-fail paths raise a typed exception (`ShadowIrreversibilityError`); soft-fail paths populate `warnings`. Dispatch coordinators are forced to choose: handle the exception (abort) or read `warnings` (record and proceed).

**When to use:** Any API surface that spec-mandates a quality-test split — some checks abort, others record. Encoding the split in two different mechanisms (exception vs collected list) makes the audit obligation visible at the call site.
**Source:** 02-03-SUMMARY.md (OQ-3)

---

### `typing.Protocol` with `@property` for read-only attributes that frozen dataclasses can satisfy
A `Protocol` declaring `rules: tuple[PathRule, ...]` as a class variable is read-write to mypy; a frozen dataclass cannot satisfy it. Rewriting as `@property def rules(self) -> tuple[PathRule, ...]: ...` makes the Protocol read-only; frozen dataclasses' auto-generated read-only attributes satisfy it without any `# type: ignore`.

**When to use:** Any Protocol whose intended implementers are frozen dataclasses (the common case for immutable value types). Class-variable Protocols are appropriate only when implementers are expected to be mutable.
**Source:** 02-02-SUMMARY.md (W7)

---

### Grep-gate acceptance tests with line-anchored regex (not bare pattern match)
`grep -n '^\s*@lru_cache' src/photophore/shadow/` not `grep -n '@lru_cache' src/photophore/shadow/`. The line-anchor + leading-whitespace prefix targets decorator-application AT use-site, not prose mentions in docstrings or comments. Same pattern: `^\s*@functools\.cache`, `^\s*_shadow_cache\s*=` for assignment-style gates.

**When to use:** Any "this token must not appear as actual code" lint where the token is also likely to appear in legitimate documentation explaining its prohibition. AST-based lints (Phase 1 pattern) are stronger but heavier; line-anchored grep is the lightweight workable middle.
**Source:** 02-02-SUMMARY.md, 02-03-SUMMARY.md

---

### Hypothesis outer-`@given` × inner-`range()` loop for no-content-keyed-cache proofs
`@given(content=binary(min_size=1, max_size=10_000)) @settings(max_examples=100)` outer + `for _ in range(100):` inner = 10,000 calls per test invocation, all with identical content per outer draw. Assert all 10,000 shadow_ids are distinct → proves no module-level cache keyed on content.

**When to use:** Behavioral proofs of "no caching" for stateless-by-contract functions. The inner range provides the same-input-multiple-times signal that a unit test cannot generate from a single fixture; the outer `@given` ensures we exercise many input shapes.
**Source:** 02-03-SUMMARY.md

---

### Three-store mandate enforced by separate filesystem paths
Trust store (keystore via `python-keyring`) + metadata index (`channels.db`) + audit log (`audit.db`) → three discrete stores, three files. AT-A5 (trust-store co-location) is satisfied structurally because the keystore is platform-managed and the two SQLite files are explicit different paths; a structural test asserts the paths are distinct.

**When to use:** Spec-mandated separation between different trust/storage roles. Logical separation alone (e.g., "different tables in one DB") is insufficient — physical separation by file makes the property auditable by anyone with `ls`.
**Source:** 02-CONTEXT.md (D-04), 02-01-SUMMARY.md

---

### Phase-tagged conformance fixtures in MANIFEST.yaml (carried from Phase 1 D-04)
Every fixture entry carries a `phase: N` tag declaring which phase wires it behaviorally. AT-A1 lands structurally in Phase 2 with `phase: 3` (dispatch coordinator owns the wire); AT-A4/A5 wired behaviorally in Phase 2; AT-A2 wired behaviorally via Hypothesis in Plan 02-03. Cross-phase reviewers can grep by phase tag to find their wiring obligations.

**When to use:** Cross-language conformance corpora that ship structurally before all phases can wire them behaviorally. The phase tag prevents structural-only fixtures from looking identical to wired ones — same pattern as Phase 1.
**Source:** 02-01-SUMMARY.md, 02-03-SUMMARY.md

---

### Cross-impl spec patch via `thermocline/CHANGELOG.md` + schema regeneration + backward-compat alias
When implementation discovers a privacy primitive's surface needs widening, the spec moves, not the implementation. Pattern: (1) rename type in `thermocline.envelope`, (2) add to `__all__`, (3) run `python -m thermocline.scripts.build_schemas --write` to regenerate the 5 schema artifacts, (4) record in `thermocline/CHANGELOG.md` under the next minor version as a cross-implementation contract event, (5) keep a backward-compat alias for one release. Second occurrence of the pattern (Phase 1 = cirdan→thermocline; Phase 2 = `_ResultPolicy`→`ResultPolicy`).

**When to use:** Any time a Phase 2+ implementation discovers a Phase-1-shipped type needs broader visibility, renaming, or shape change. The CHANGELOG entry is what makes the change discoverable to Rust/TypeScript ports; the alias prevents in-tree caller churn during transition.
**Source:** 02-03-SUMMARY.md, Phase 1 THERMO-01 precedent

---

## Surprises

### `python-keyring` has no enumerate-by-service API at all
This was not flagged in the Phase 2 context-gathering stage. Discovered during 02-RESEARCH while pricing D-05 keystore-as-truth bootstrap. The library wraps platform keystores that themselves *do* support enumeration on most platforms (Keychain `security` CLI on macOS, libsecret on Linux) — but the Python binding deliberately doesn't expose it. The `_index` sentinel pattern is therefore a hard requirement, not an optimization.

**Impact:** Lifted from "implementation detail" to D-05/OQ-1 architectural decision; added complexity to channel-store atomic-write ordering (D-07 step 1 now also updates `_index`).
**Source:** 02-RESEARCH.md, 02-01-SUMMARY.md

---

### SQLite multi-row inserts in the same millisecond fail timestamp-based ordering
A trivially fast test (`audit.append() ; audit.append() ; audit.append()`) lands all three rows within the same millisecond on modern hardware. UUIDv4 row IDs randomize the secondary sort. The chain hash test `test_third_entry_prev_hash_equals_second_entry_hash` failed nondeterministically until ordering switched to `rowid DESC`.

**Impact:** Surfaced an entire class of bug (timestamp-based ordering for insertion-recency) that was silently invisible until the chain hash test demanded strict insertion order. Lesson now in the patterns above.
**Source:** 02-01-SUMMARY.md

---

### `pathspec`'s deprecated pattern name silently spammed 72 warnings without test failure
`pathspec.PathSpec.from_lines("gitwildmatch", ...)` produces correct results AND emits a DeprecationWarning per call. Tests passed; the warnings only surfaced because pytest is configured to print them. Easy to miss in CI noise. The fix (`"gitignore"`) is identical-semantics and zero-risk, but the misleading "test green" status disguised a real maintenance issue.

**Impact:** Generalizes: `pytest -W error::DeprecationWarning` is the safe-default for new Phase 2+ test runs. CI should escalate DeprecationWarning to error for libraries in the core dependency surface.
**Source:** 02-02-SUMMARY.md

---

### Source-grep acceptance tests trip on prose mentions of the forbidden token
`test_engine_has_no_tier_local_literals` and `test_shadow_no_caching` both fired on docstrings that *documented the prohibition*. The fix (line-anchored regex) is straightforward, but the surprise was that "explain why this is forbidden" in a docstring fails a grep-based gate enforcing the prohibition. Two independent occurrences in Phase 2 confirmed it's a pattern, not a one-off.

**Impact:** Established the line-anchored grep convention; influenced POLICY-01's comment phrasing (paraphrased to avoid matching the grep gate for `envelope_draft["result_policy"]` access).
**Source:** 02-02-SUMMARY.md, 02-03-SUMMARY.md

---

### "credential of type X" abstraction vocabulary leaked through the irreversibility test
The text the shadow generator emits to describe credentials shares the 8-char substring "credenti" with the source content it's abstracting. The irreversibility test caught this *correctly* — it's literally the test's job — but the cause was the abstraction's word choice, not real leakage. Vocabulary-overlap-as-false-positive is a recurring failure mode.

**Impact:** Established the "shadow labels avoid vocabulary correlated with their source content" rule. Generalizes to any future content type added in v0.2+ (e.g., a `BIOMETRIC` type should not label as "biometric data" if that phrase is likely in raw source).
**Source:** 02-03-SUMMARY.md

---

### 4-character irreversibility threshold matches common English bigram-pairs
"at", "of", "in", "to", "the" all match an 8-char window of any abstraction containing them. A 4-char floor would fire on every shadow whose label uses the English determiner system. Required empirical re-tuning against a realistic corpus.

**Impact:** Lifted `_IRREVERSIBILITY_MIN_SUBSTR_LEN` to 8. Documented in 02-RESEARCH §7. Generalizes: any privacy threshold tuned by intuition deserves an empirical sweep against a corpus that includes innocuous English prose.
**Source:** 02-03-SUMMARY.md

---

### Making `ResultPolicy` public required a 5-file schema regeneration + CHANGELOG cross-impl entry + 142-test re-verification
What looked like a one-line `__all__` patch was actually a 7-file cross-cutting change: `envelope.py` (rename + backward-compat alias), `__init__.py` (add to `__all__`), `task.schema.json` + `job.schema.json` (`$defs` key change from `_ResultPolicy` to `ResultPolicy`), `CHANGELOG.md` (cross-impl contract record), and a full Phase 1 test re-run to confirm nothing broke. Second occurrence of "spec patch from implementation" (Phase 1 THERMO-01 was the first).

**Impact:** Established the cross-impl-spec-patch pattern as a Phase 2+ regular event. Confirms the schema regeneration pipeline (Phase 1 D-02) is correctly load-bearing — without the `--check` drift gate, the `$defs` key would have desynced silently.
**Source:** 02-03-SUMMARY.md

---

### Worktree-isolated executors committed directly on `main` (recurrence from Phase 1)
The Phase 1 LEARNINGS noted this anti-pattern. Phase 2 executors exhibited the same behavior — `git log --first-parent main` shows all Plan 02-01/02-02/02-03 commits on `main` despite the executor harness contract for worktree isolation. Same observation; same zero downstream impact (commits were correct); same unresolved safety property.

**Impact:** Confirms the Phase 1 observation is a stable harness behavior, not a per-session accident. Forward-looking note (per .continue-here.md): if Phase 3 exhibits the same, escalate as a real harness bug rather than continuing to "log it and proceed."
**Source:** Multiple SUMMARY files; 02-DISCUSSION-LOG.md context

---

### Stale `.pth` files from cleaned-up worktrees broke `import thermocline` on Plan 02-01 startup
The system Python's editable install for `thermocline` was pointing at a worktree path from a previous session that had since been deleted by harness cleanup. `import thermocline` raised `ImportError: No module named 'thermocline'` despite the package being installed. Caught immediately on Task 1's first import; resolved by `pip install -e` against the canonical source.

**Impact:** Surfaced a system-level dev-environment fragility orthogonal to plan correctness. Generalizes: any session that uses worktree isolation must `pip install -e` against canonical paths in conftest/setup, not assume the system Python is consistent.
**Source:** 02-01-SUMMARY.md

---

### `click.testing.CliRunner` mixes stderr error lines into `result.output` by default
Tests that assert `json.loads(result.output)` work fine on success paths and fail on error paths because click appends `Error: ...` lines after the JSON. The default `mix_stderr=True` is the convenience default — for JSON-output tests it's a footgun. Documented in click, but the surprise was that it cost a debugging round to identify.

**Impact:** Future CLI tests in `photophore` (and the upcoming `dispatch` CLI in Phase 3) should default to `CliRunner(mix_stderr=False)` for JSON-output assertions OR explicitly filter `"Error: "` prefixes before parse. Generalizes to any Phase 3+ CLI test in this codebase.
**Source:** 02-01-SUMMARY.md

---

