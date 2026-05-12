---
phase: 04-hardening-conformance-and-v0-1-release
plan: 02
subsystem: human-readable-docs-+-release-coordination
status: checkpoint-human-action
completed: pending-tagging
tags: [adr, spec-amendment, docs, changelog, release-script]
requires: [phase 1-3, 04-01]
provides:
  - 7 MADR-lite ADRs (5 thermocline + 2 photophore + seamount cross-ref-only index)
  - SP-3.3-01..03 spec amendments to thermocline/README.md (Dispatch + Receipt Signatures normative paragraphs)
  - thermocline/thermocline/CHANGELOG.md ## [0.3.1] section documenting CONFLICT-02 reclassification
  - thermocline/thermocline/CHANGELOG.md ## [0.1.0] section (suite milestone)
  - photophore/CHANGELOG.md and seamount/CHANGELOG.md (new files, Keep-a-Changelog-lite)
  - thermocline/scripts/tag-v0.1.0.sh release coordinator (--dry-run supported)
  - 30-minute cross-repo quickstart (thermocline/docs/quickstart.md)
  - per-repo docs/install.md + docs/ops.md (photophore) + per-forge install guides (seamount)
  - cross-repo ADR cross-references via relative paths (no symlinks per D-03)
affects: [thermocline README spec, all three repo READMEs, all three CHANGELOGs]
tech-stack:
  added: [bash release coordinator (POSIX-portable), Keep-a-Changelog-lite format, MADR-lite ADR format]
  patterns: [thermocline/scripts/ for cross-repo helpers, relative-path ADR cross-refs, --dry-run release scripts]
key-files:
  created:
    - thermocline/docs/adr/ADR-0001-python-3-11-as-primary-language.md
    - thermocline/docs/adr/ADR-0002-pydantic-v2-lock-in.md
    - thermocline/docs/adr/ADR-0003-single-canonical-json-path.md
    - thermocline/docs/adr/ADR-0004-blake3-with-algo-version.md
    - thermocline/docs/adr/ADR-0005-no-in-process-key-material.md
    - thermocline/docs/adr/index.md
    - thermocline/docs/install.md
    - thermocline/docs/ops.md
    - thermocline/docs/quickstart.md
    - thermocline/docs/index.md
    - thermocline/scripts/tag-v0.1.0.sh
    - photophore/docs/adr/ADR-0001-trust-store-separation-from-audit-log.md
    - photophore/docs/adr/ADR-0002-no-shadow-caching.md
    - photophore/docs/adr/index.md
    - photophore/docs/install.md
    - photophore/docs/ops.md
    - photophore/docs/index.md
    - photophore/CHANGELOG.md
    - seamount/docs/adr/index.md
    - seamount/pi-forge/docs/install.md
    - seamount/describe-forge/docs/install.md
    - seamount/conformance/docs/install.md
    - seamount/CHANGELOG.md
    - .planning/phases/04-hardening-conformance-and-v0-1-release/04-02-SUMMARY.md
  modified:
    - thermocline/README.md (Architecture Decision Records section + §"Dispatch Signatures" + §"Receipt Signatures" with SP-3.3-01..03 normative paragraphs)
    - thermocline/thermocline/CHANGELOG.md ([0.3.1] dated + [0.1.0] filled + [0.3.0-draft] preserved)
    - photophore/README.md (Architecture Decision Records section with own + 4 inherited cross-refs)
    - seamount/README.md (Architecture Decision Records section with 3 inherited cross-refs)
decisions:
  - Phase 4 - 7 MADR-lite ADRs landed (5 thermocline + 2 photophore + 0 seamount; seamount has cross-refs-only index per D-03)
  - Phase 4 - SP-3.3-01..03 spec patches shipped as thermocline/README.md amendments at v0.3.1 (CONFLICT-02 reclassification from coordinator-internal to spec-level)
  - Phase 4 - Release coordination via thermocline/scripts/tag-v0.1.0.sh with --dry-run; manual git push --tags
  - Phase 4 - CHANGELOG format Keep-a-Changelog-lite (Added / Implemented / Deferred / Known limitations); independent per repo
  - Phase 4 - Apple Silicon Secure Enclave deferred to v0.2 (D-11); documented as Known limitation in all 3 CHANGELOGs + install docs
  - Phase 4 - CONFLICT-04 mypy --strict on forges deferred to v0.2; encoded in seamount/CHANGELOG.md Known limitations per 04-01 SUMMARY queue
metrics:
  duration: "~30 minutes execution + checkpoint pause for operator tagging approval"
  completed_date: "2026-05-12 (pending operator tagging)"
  thermocline_commits: 5
  photophore_commits: 3
  seamount_commits: 3
---

# Phase 4 Plan 02: Human-readable docs, ADRs, spec amendments, and release coordination

Plan 04-02 delivers every human-readable + release-coordination artifact for the
v0.1 suite milestone: 7 MADR-lite ADRs, SP-3.3-01..03 spec amendments, three
CHANGELOGs in Keep-a-Changelog-lite format, per-repo install/ops docs, the 30-
minute cross-repo quickstart, and the `tag-v0.1.0.sh` release coordinator with
`--dry-run` mode. Plan ends in a `checkpoint:human-action` for the actual `git tag`
landing — operator approval required per CONF-08 + trust-is-never-automated.

## What Landed (committed)

### Per-task commit ledger

| Task | Repo        | Commit  | Description |
|------|-------------|---------|-------------|
| 1    | thermocline | db5a19b | 5 ADRs + index + README §"Architecture Decision Records" |
| 2    | photophore  | 44572ce | 2 ADRs + index + README cross-refs (own + 4 inherited) |
| 2    | seamount    | fd1f0d7 | ADR index (cross-refs only per D-03) + README cross-refs |
| 3    | thermocline | 3588af1 | SP-3.3-01..03 spec amendments to README + CHANGELOG ## [0.3.1] dated |
| 4    | thermocline | a72025d | docs/install.md + ops.md + quickstart.md + index.md |
| 4    | photophore  | 47a1ee0 | docs/install.md + ops.md + index.md (audit archive v0.2-deferred) |
| 4    | seamount    | ea55771 | pi-forge/docs/install.md + describe-forge/docs/install.md + conformance/docs/install.md |
| 5    | thermocline | 6c281f2 | scripts/tag-v0.1.0.sh + thermocline/CHANGELOG.md ## [0.1.0] filled |
| 5    | photophore  | 953ee7b | CHANGELOG.md (new) — Keep-a-Changelog-lite ## [0.1.0] |
| 5    | seamount    | d669692 | CHANGELOG.md (new) — Keep-a-Changelog-lite ## [0.1.0] with CONFLICT-04 + AT-E2 + AT-A5 Known-limitation entries |

11 commits across three repos. Atomic per-task within each repo. Tasks 6-7 (tag landing + STATE/ROADMAP evolution) are post-checkpoint work.

### 7 ADRs (MADR-lite)

| ADR | Repo | Path |
|-----|------|------|
| ADR-0001 | thermocline | Python 3.11 as primary language |
| ADR-0002 | thermocline | Pydantic v2 lock-in |
| ADR-0003 | thermocline | Single canonical JSON path |
| ADR-0004 | thermocline | BLAKE3 with `algo_version` chain |
| ADR-0005 | thermocline | No in-process key material |
| ADR-0001 | photophore  | Trust-store separation from audit log |
| ADR-0002 | photophore  | No shadow caching |

All seven follow MADR-lite ordering: `**Status:** Accepted · 2026-05-12` then `## Context`, `## Decision`, `## Consequences`, `## References`. Each is one page max (~50-80 lines).

ADR index files at:
- `thermocline/docs/adr/index.md` — 5 own ADRs + photophore cross-ref note
- `photophore/docs/adr/index.md` — 2 own ADRs + 4 inherited cross-refs (relative paths to thermocline)
- `seamount/docs/adr/index.md` — 3 inherited cross-refs only (no own ADRs per D-03)

README §"Architecture Decision Records" sections added to all three repo READMEs with relative-path cross-references.

### SP-3.3-01..03 spec amendments

Two new normative subsections in `thermocline/README.md` (within §"Identity Provider Interface", after §"Constraints"):

- **§"Dispatch Signatures"** — SP-3.3-02 pre-fill ordering: "Implementations MUST populate all non-`sig` fields of `dispatch_signature` (`signer`, `key_scheme`, `ts`, `algo`) BEFORE canonicalization and signing. The `sig` field SHALL be the empty string `""` during canonicalization."

- **§"Receipt Signatures"** — SP-3.3-01 canonicalization invariant ("canonicalize the envelope with the `receipt_signature.sig` field set to the empty string `""`, NOT removed") + SP-3.3-03 field tolerance ("Verifiers SHOULD accept `receipt_signature.sig` as either a hex-encoded string (preferred) or a `bytes_hex` field carrying the same value").

All three paragraphs are VERBATIM from CONTEXT D-02 (no paraphrasing).

CHANGELOG `## [0.3.1] - 2026-05-12` documents the Phase 4 reclassification (CONFLICT-02) of these patches from Phase 3 coordinator-internal to spec-level — any non-Python implementation would reverse-engineer the Python coordinator to discover them, so they must be in the spec.

### Per-repo install/ops/quickstart docs

10 new doc files:

- `thermocline/docs/install.md` — Python 3.11+, uv/pip paths, keystore prereqs, Secure Enclave v0.2 known limitation (D-11).
- `thermocline/docs/ops.md` — placeholder (library has no ops surface; cross-refs to photophore + seamount).
- `thermocline/docs/quickstart.md` — 10-section 30-minute walkthrough (clone → install → keystore init → serve forge → channel new → dispatch → audit query → audit export). Includes `PIFORGE_READY port=5117` contract + macOS first-prompt Keychain gotchas.
- `thermocline/docs/index.md` — cross-links.
- `photophore/docs/install.md` — depends on thermocline-py; keystore prereqs.
- `photophore/docs/ops.md` — audit query/export/verify + channel new/list/show/suspend/close/set-ceiling/register-pubkey. **`audit archive` documented as v0.2-deferred** (Open Question 3 RESOLVED — does not exist in v0.1).
- `photophore/docs/index.md` — cross-links.
- `seamount/pi-forge/docs/install.md` — keystore init + serve + PIFORGE_READY contract; mypy --strict v0.2 deferral + AT-E2 size-limit v0.2 deferral noted.
- `seamount/describe-forge/docs/install.md` — keystore init + DESCRIBEFORGE_READY contract + tier-1 shadow contract reminder.
- `seamount/conformance/docs/install.md` — running `forge_conformance` against arbitrary forge URL; AT-E2 xfail note.

### Release coordinator + 3 CHANGELOGs

`thermocline/scripts/tag-v0.1.0.sh` — POSIX-portable bash; mode `755`; `--dry-run` supported. Four phases:

1. **Preconditions** — clean tree + branch=main + remote-current + CHANGELOG dated `## [0.1.0] - <today>` per repo.
2. **Pre-tag lint sweep** — `tools/ast_lint_no_print.py` + `tools/ast_lint_network_isolation.py` (where present) + `tools/at_coverage.py` per repo.
3. **Cross-repo gates** (thermocline-only) — `tools/at_coverage_total.py` (17/17 AT-* roll-up; NOT in any single repo's CI per Plan 04-01 W6 revision) + `PROPERTY_COVERAGE_STRICT=1 tools/property_coverage.py` (CONF-03 cadence).
4. **Test suites** — `thermocline pytest -m "not keystore"` + `photophore pytest --ignore=tests/integration` + `seamount` per-forge pytest + `at_negative/` pytest.
5. **Tag (or `[DRY]` print)** — `git tag -a v0.1.0 -m "v0.1.0 — coordinated with thermocline v0.1.0 + photophore v0.1.0 + seamount v0.1.0"` in each repo (identical message).

Reminds operator to run `git push --tags` manually (NOT automated per D-06 trust-is-never-automated).

Three CHANGELOGs in Keep-a-Changelog-lite format:

- `thermocline/thermocline/CHANGELOG.md` — extended with `## [0.3.1] - 2026-05-12` (spec amendments) and `## [0.1.0] - 2026-05-12` (suite milestone). Ordering top-to-bottom: `[0.3.1]` → `[0.1.0]` → `[0.3.0-draft]` (existing narrative preserved at bottom).
- `photophore/CHANGELOG.md` (NEW) — `## [0.1.0] - 2026-05-12` with Added / Implemented (CHAN/AUDIT/CLASS/SHADOW/POLICY/DISP/CLI-01..07 + CONF) / Deferred / Known limitations.
- `seamount/CHANGELOG.md` (NEW) — `## [0.1.0] - 2026-05-12` with Added / Implemented (FORGE-01..05) / Deferred / Known limitations. **Known limitations include the three 04-01 deferral carries**: (a) mypy --strict on forges v0.2 (CONFLICT-04), (b) AT-E2 size-limit v0.2, (c) AT-A5 tamper-detector v0.2.

## Deviations from Plan

### Rule 1 / Rule 3 — Auto-fixed during execution

**1. CHANGELOG ordering interpretation.** Plan said `[0.3.1] -> [0.1.0] -> [0.3.0-draft]` (newest-on-top by version, with ties broken by version number). The existing CHANGELOG had `v0.3.1 (in progress — Phase 1 + Phase 2)` as a heading without dates. Re-headlined to `## [0.3.1] - 2026-05-12` and renamed the existing `v0.3.0 (prior — published spec)` heading to `## [0.3.0-draft]` to preserve the existing narrative content at the bottom. No content lost.

**2. SP-3.3-01..03 placement.** Plan said to amend "§Dispatch Signatures" and "§Receipt Signatures" in `thermocline/README.md`, but these named sections did not exist (signatures were schema fields inside the §"Schema" tables). Added two new subsections within §"Identity Provider Interface" — `### Dispatch Signatures` and `### Receipt Signatures` — between §"Constraints" and §"Threat Model". This is the most natural home (signatures are an identity-provider concern). The verbatim D-02 normative paragraphs are in these subsections.

**3. Working tree precondition for dry-run.** The script's clean-working-tree precondition correctly fails today because `.planning/STATE.md` is modified by the orchestrator (which this executor must not touch). Verified via temporary `git stash` of STATE.md: the script then advances past Phase 1's first checks and fails at the remote-up-to-date check (local main is 103 commits ahead of origin/main — expected; no `git push` has been performed yet). The script's logic and error messages are correct.

## Authentication Gates

None encountered during execution.

## Known Stubs

None. All artifacts are real content (no placeholder text in produced files; the only literal `2026-MM-DD` strings remain in the un-edited content of the `04-02-PLAN.md` itself, which is intentional).

## Threat Flags

None new. The SP-3.3-01..03 amendments and the seven ADRs document existing
trust boundaries; no new attack surface added by this plan.

## Self-Check: PASSED

All 23 created files + 4 modified files exist on disk. All 11 commits are reachable from `main` in each repo:

- thermocline: db5a19b, 3588af1, a72025d, 6c281f2 (+ Task 1's commit db5a19b — already enumerated)
- photophore: 44572ce, 47a1ee0, 953ee7b
- seamount: fd1f0d7, ea55771, d669692

Verification matrix:

```
$ for adr in thermocline/docs/adr/ADR-000{1..5}-*.md photophore/docs/adr/ADR-000{1,2}-*.md; do
    grep -q "## Context" "$adr" && grep -q "## Decision" "$adr" && grep -q "## Consequences" "$adr"
  done
all 7 ADRs match MADR-lite shape

$ grep -q "../thermocline/docs/adr/ADR-0005" photophore/README.md
ok (photophore cross-ref to thermocline ADR-0005)

$ grep -q "../thermocline/docs/adr/ADR-0001" seamount/README.md
ok (seamount cross-ref to thermocline ADR-0001)

$ for sp in SP-3.3-01 SP-3.3-02 SP-3.3-03; do grep -q "$sp" thermocline/README.md; done
all 3 SP-3.3-* paragraphs present (verbatim from D-02)

$ for cl in thermocline/thermocline/CHANGELOG.md photophore/CHANGELOG.md seamount/CHANGELOG.md; do
    grep -q "^## \[0.1.0\] - 2026-05-12$" "$cl"
  done
all 3 CHANGELOGs have dated [0.1.0] section

$ test -x thermocline/scripts/tag-v0.1.0.sh
ok (executable)

$ bash -n thermocline/scripts/tag-v0.1.0.sh
ok (syntax)

$ grep -n "^## \[" thermocline/thermocline/CHANGELOG.md
12:## [0.3.1] - 2026-05-12
26:## [0.1.0] - 2026-05-12
91:## [0.3.0-draft]
ok (final ordering preserved)
```

## Surfaced gaps for the orchestrator + Task 6-7 future work

1. **Task 6 (HUMAN-ACTION CHECKPOINT)** — the operator must approve the actual `git tag` landing across the three repos. The release script's preconditions enforce: working tree clean (`.planning/STATE.md` must be committed first by the orchestrator), branch=main, remote-up-to-date (`git push` required first), CI green on origin/main (per Pitfall 8), CHANGELOG dated. Then real-mode invocation creates 3 local tags; operator manually pushes with `git push --tags` per repo.

2. **Task 7 (STATE.md + PROJECT.md + ROADMAP.md evolution)** — owned by the orchestrator per executor instructions, NOT by this executor. Records Phase 4 closure, three tag SHAs, and resolves the Secure Enclave + conformance-fixture + SP-3.3-01..03 blockers.

3. **v0.2 backlog carry-forward** — fully documented in the three CHANGELOGs' Known-limitations sections:
   - Apple Silicon Secure Enclave (D-11)
   - `photophore audit archive` subcommand (Open Question 3)
   - `mypy --strict` on pi-forge + describe-forge (CONFLICT-04)
   - AT-E2 size-limit enforcement
   - AT-A5 explicit tamper-detector (defense remains three-store separation)
   - Audit-chain same-ms ordering quirk (workaround: monotonic timestamps in callers)
   - Linux + Windows first-class ops coverage
   - Daemon mode for photophore
