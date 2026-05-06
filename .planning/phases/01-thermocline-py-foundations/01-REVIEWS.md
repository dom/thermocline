---
phase: 1
reviewers: [ollama]
reviewed_at: "2026-05-06T04:52:08Z"
plans_reviewed:
  - 01-01-PLAN.md
  - 01-02-PLAN.md
  - 01-03-PLAN.md
ollama_model: glm-4.7-flash:latest
ollama_endpoint: http://localhost:11434
notes: |
  Single-reviewer pass. Other CLIs unavailable on this host:
  - claude CLI installed but skipped per workflow's self-skip rule
    (running inside Claude Code; CLAUDE_CODE_ENTRYPOINT=cli).
  - gemini, codex, coderabbit, opencode, qwen, cursor: not installed.
  - lm_studio, llama_cpp: no local server on standard ports.
  glm-4.7-flash is a thinking model — model-internal reasoning is preserved
  below for traceability; the Review Report section is the model's final answer.
---

# Cross-AI Plan Review — Phase 1: `thermocline-py` Foundations

## Ollama Review (`glm-4.7-flash:latest`)

# Peer Review Report: Thermocline Suite Phase 1 (v0.1)

## 1. Summary
The Phase 1 implementation plan for the **Thermocline Suite** is technically robust, strictly scoped, and demonstrates a high degree of rigor in defining cryptographic boundaries and inter-process contracts. The distribution of work into three waves successfully isolates foundational libraries (01-01), cryptographic primitives (01-02), and verification contracts (01-03). The plans exhibit strong awareness of "Pitfall" security risks (e.g., silent logging, key leakage, JSON serialization discrepancies).

However, specific loopholes in runtime safety (the Receipt constructor) and edge-case behavior of the `Sensitive[T]` wrapper under Pydantic v2's advanced mutation methods (e.g., `model_construct`) are not explicitly covered by acceptance criteria. Risk is *Medium* due to potential friction with platform keyring ecosystems in constrained environments (Linux containers) rather than logical gaps in the spec.

## 2. Strengths
- **Strict Type Safety & Linting**: The explicit use of `mypy --strict` and hardcoded `grep` checks for serialization methods (`.dict()`, `.json()`, `json.dumps`) effectively closes the door on common Pydantic v1/v2 migration pitfalls (Pitfalls 11 & 12).
- **Negative Test Coverage**: Plan 01-03 provides a comprehensive utility of negative test cases (AT-C1..AT-C6). Instead of assuming everything works, the fixture set explicitly tests replay, tampering, and extraneous fields.
- **Public API Discipline**: The requirement to pin `canonicalize` to `rfc8785` via AST checking ensures cross-language implementation parity, which is a critical requirement for a *distributed* architecture.
- **Keystore Hardening**: The identification of `IDENT-05` and the requirement to throw `KeystoreUnavailableError` at startup if `python-keyring` fails prevents "convenient" but insecure fallback routes (e.g., reading keys from a local file).

## 3. Concerns

### HIGH: D-01 Runtime Loopholes (Plan 01-03)
*The `Receipt` private constructor relies on a sentinel token (`_RECEIPT_TOKEN`). While static typing (`mypy`) is enforced and a misuse fixture is provided, there is no test coverage for runtime bypass attempts using Pydantic/Dataclass internals.*
- **Concern**: `dataclasses.replace` allows creation of a new `Receipt` instance with identical fields, bypassing `__init__` and thereby bypassing the token check. `copy.copy` and `pickle` (via `__reduce__`) are also technically possible bypass vectors for frozen dataclasses.
- **Missing**: "Cannot verify via `dataclasses.replace(x)`" or "Cannot verify via `copy.copy(x)`".
- **Mitigation**: The plan implies `frozen=True`, but `dataclasses.replace` is specifically documented to work on frozen instances. If the plan relies *only* on `mypy` for D-01, it risks a CI-passing runtime vulnerability.

### MEDIUM: `Sensitive[T]` Wire Transparency (Plan 01-01 & 01-02)
*Plan 01-01 defines `Sensitive[bytes]`, and Plan 01-02 assumes canonical-JSON round-trip stability. However, the plan does not explicitly verify behavior through `model_construct`.*
- **Concern**: Pydantic v2's `model_construct` bypasses field validation and serialization logic. If an envelope is constructed via `envelope.model_construct(...)` where the `Sensitive` payload is passed unparsed (bare bytes) or mis-typed, does the canonical serializer still trigger? This determines if the type discipline is enforced at the API boundary.
- **Missing**: A test in 01-02 that constructs an envelope via `model_construct` and asserts that `CanonicalizationError` is raised *if* non-canonical types are passed, or that serialization behaves correctly *if* canonical types are passed.

### MEDIUM: IDENT-05 Environment Robustness (Plan 01-03)
*Requirements specify "Platform secure keystore (separate from SQLite by mandate)."*
- **Concern**: While the code forbids file/env storage, it does not explicitly verify robustness in headless environments (e.g., Linux containers without a Display Server). If `python-keyring` is installed but its backend requires ` dbus` or `X11` session state, the application fails to start. The current check only validates if `NoKeyringError` is raised, but not if the *backend* is viable.
- **Mitigation**: The check `python-keyring` cannot reach... is good, but adding a specific CI test that spins up a minimal container with `keyring` installed but no session (mocking the backend) would be a stronger verification.

### LOW: Pitfall 11 Allowlist Execution (Plan 01-02)
*The script `check_no_json_dumps` uses an AST visitor. This generally catches `json.dumps`.*
- **Concern**: The allowlist is static. If a developer imports the `json` library dynamically (e.g., `mod = __import__('json')`) and accesses `mod.dumps`, AST visits might catch this if the call is static in the module source, but dynamic imports of unrelated JSON libraries (e.g., third-party dependency using `json.dumps` incorrectly) would not be caught by this lint.
- **Verdict**: Low Risk, as the lint is for *development discipline*, not library auditing.

## 4. Suggestions

1.  **D-01 Runtime Validation**: Add a specific unit test in `test_identity_receipt_private.py` (Plan 01-03) to verify that `copy.copy(receipt)` returns `None` or a non-`Receipt` instance, or raises a custom exception, rather than just passing the check.
2.  **Sensitive Wire Transparency**: Add a test covering `model_construct` in the canonical round-trip test (Plan 01-02). Assert that providing non-canonical types (e.g., raw dicts) during construction triggers the expected error handling path.
3.  **Keyring CI Precondition**: In the CI definition (not shown, but inferred), explicitly document the requirement for a functional python-keyring backend. Consider adding a CI step that sets a dummy keyring backend just to ensure the *sign/verify* path (using pre-seeded keys) can be tested without real OS security tools, while retaining the *startup* guard logic.
4.  **AT-C Fixture Scope**: Ensure that AT-C1 (Replayed) actually generates a *new* signature based on a replay attempt, or simply asserts that parsing fails. The plan implies it is an invalid fixture, which satisfies the requirement.

## 5. Risk Assessment
**Medium**

**Justification**:
The architectural logic is sound, but the **private constructor vulnerability** represents a valid, albeit subtle, escape hatch for runtime bypass. Additionally, the **IdentityProvider integration** with platform systems (Keychains/DBus) carries environmental risk. If the strict "no fallback" rule (IDENT-05) is too rigid for standard deployment containers (e.g., AWS Lambda / Headless Docker), the implementation becomes fragile rather than secure. However, assuming standard desktop/server OS environments, the risk is contained. The dependency chain is sound.
---

<details>
<summary>Model reasoning trace (preserved for traceability)</summary>

1.  **Understand the Goal**: The user wants me to act as an independent peer reviewer for the "Thermocline Suite" implementation plans. I need to review plans 01-01, 01-02, and 01-03 for completeness, soundness, and risk, specifically looking for pitfalls like the sentinel, keystore robustness, wire-transparency, lint loopholes, and dependency management.

2.  **Analyze the Plan Context (Thermocline Suite)**:
    *   **Project**: Privacy-tiered task-dispatch architecture for distributed AI nodes.
    *   **Core Value**: "Reveal only what the receiver needs... tier-0 content never leaves" + verifiable privacy receipts.
    *   **Phase 1 Goal**: Build `thermocline-py` (envelope types, canonical JSON, IdentityProvider, schemas).
    *   **Locked Design Decisions (D-01, D-02, etc.)**: I need to take these as "truth" for the review but verify if the implementation plans satisfy them.

3.  **Review Plan-by-Plan (Mental Walkthrough)**:

    *   **Plan 01-01 (Package & Envelopes)**:
        *   *Objective*: Scaffold package, Pydantic models, `Sensitive[T]`, JSON Schema generation.
        *   *Key Specs*: `ConfigDict(extra="forbid")`, `Sensitive[bytes]`, `SUPPORTED_VERSIONS`.
        *   *Pitfall 12*: Checking for `.dict()` or `.json()` usage. This is good because Pydantic v2 models often have hidden interactions.
        *   *Pitfall 11*: Checking for `json.dumps`.

    *   **Plan 01-02 (Canonical JSON)**:
        *   *Objective*: Single source of truth for canonicalization.
        *   *Key Specs*: `rfc8785`, lint script `check_no_json_dumps`.
        *   *Hypothesis Tests*: Round-trip stability.

    *   **Plan 01-03 (Identity & Conformance)**:
        *   *Objective*: Crypto, Receipt construction, Conformance fixtures.
        *   *Key Specs*: `IdentityProvider` Protocol, `BrineProvider` (PyNaCl), `Receipt` private constructor.
        *   *Conformance*: 6 AT-C fixtures.

4.  **Deep Dive into Specific Review Instructions**:

    *   **D-01 Sentinel (Runtime/Static)**:
        *   *Plan 01-03 Task 1*: Defines `_RECEIPT_TOKEN`.
        *   *Concern*: Does `dataclasses.replace`, `copy.copy`, or `pickle` allow bypassing? The plan mentions `mypy --strict` checks the misuse fixture, but doesn't explicitly check for `replace`, `copy`, or `pickle` in the automated tests. A frozen dataclass prevents mutation, but construction via `__reduce__` or `dataclasses.replace` isn't explicitly guarded against.
        *   *Verdict*: MEDIUM. The sentinel logic exists, but the review notes ask me to scrutinize loopholes like `replace` and copy. The plan doesn't explicitly test these.

    *   **IDENT-05 Keystore Detection**:
        *   *Plan 01-03 Task 2*: Uses `keyring.get_keyring()`.
        *   *Concern*: `NoKeyringError` is caught. "no fall-back to file/env-var storage". Robustness against Linux containers (dbus) is a potential edge case if the container is headless or X11 is missing. But the error handling seems reasonable.
        *   *Verdict*: MEDIUM. Standard keyring logic, might fail in minimal container environments without a backend.

    *   **`Sensitive[T]` Wire Transparency**:
        *   *Plan 01-01 Task 2*: Mentions `Sensitive[bytes]`.
        *   *Concern*: In Pydantic v2, `Sensitive` needs a custom schema processor (e.g., `SkipSchema`, `PlainSerializer`). The plan assumes it's handled (D-03), but specifically checking if `model_construct` bypasses the custom serializer is a valid point. The plan doesn't explicitly list a test for `model_construct` vs `model_dump(mode='json')` behavior.

    *   **Pitfall 11 Lint Allowlist**:
        *   *Plan 01-02 Task 3*: Implements `check_no_json_dumps`.
        *   *Concern*: AST visitor checks imports of `json.dumps`. It's generally correct unless there's a dynamic import of the module or `__import__('json').dumps` which the AST handles okay, but the allowlist strategy is sound. What about `_json.dumps` or similar tricks?

    *   **Dependencies**:
        *   *Plan Sequence*: 01-01 -> 01-02 -> 01-03.
        *   *Check*: 01-02 depends on `_canonical.py` which is created in 01-02. 01-03 depends on canonical being ready for the signing step?
        *   *Observation*: The `link` in 01-03 Task 2 says `BrineProvider` calls `canonicalize`. This means `canonical.py` must be available by the time `01-03` runs. Since `canonicalize` is exposed in `__init__.py` of 01-02, and `canonical.py` is in the source tree, and 01-03 imports `thermocline.canonical`, the dependency graph is logically correct (1-01 is needed for types, 1-02 adds canonical, 1-03 uses types + canonical).

    *   **6 AT-C Fixtures**:
        *   *Plan 01-03 Task 3*:
            *   AT-C1: Replayed envelope.
            *   AT-C2: Tampered signature.
            *   AT-C3: Leaky shadow.
            *   AT-C4: Key scheme mismatch.
            *   AT-C5: Unsupported version.
            *   AT-C6: Extra field.
        *   *Assessment*: These map directly to the "Thermocline AT-C surface" labels mentioned in the plan. They seem well-crafted negative test cases.

    *   **Scope Creep**:
        *   The plan seems tightly scoped to v0.1 "foundations".

5.  **Drafting the Review**:

    *   *Summary*: Generally well-structured, technical depth is good. Plans cover the math and the "boring" infrastructure (validation).
    *   *Strengths*: Comprehensive use of Pydantic v2, strict error handling, clear negative test cases (AT-C), explicit CI linting (Pitfall 11).
    *   *Concerns*:
        *   D-01 Loopholes: Not explicitly tested.
        *   Sensitive[T] Wire Transparency: `model_construct` edge case missing.
        *   Keystore: Container environment.
    *   *Suggestions*:
        *   Add specific tests for copy/replace/pickle of Receipt.
        *   Add test for Sensitive[model_construct] vs [model_dump].
        *   Add a note/flag for headless keyring environments.
    *   *Risk*: LOW/MEDIUM. Phase 1 is technically feasible. The main risk is the interop story failing if Canonical/Envelope logic has edge cases (e.g., dates, binary data handling) not fully covered by the Hypothesis tests.

6.  **Refining the "Concerns" and "Suggestions"**:

    *   *D-01*: I need to be firm here. A frozen dataclass is good, but `dataclasses.replace` allows building a new instance with identical args, bypassing `__init__`. If `__init__` uses the token, `replace` bypasses it. The plan relies on `mypy` to catch it in *one* file, but runtime checks are needed.
    *   *Sensitive*: If the custom serializer fails, does it break JSON Schema generation? The plan in 01-01 Task 3 generates schemas from Pydantic models. If the `Sensitive` serializer breaks the schema (e.g., excludes the field), conformance fails. The plan assumes D-03 is correct, but verifying it via the schema generation is a missing link.
    *   *Dependency*: 01-01 creates `thermocline/schema`, but `pyproject.toml` in 01-02 modifies it? Wait, `pyproject.toml` defines project info. It's fine.

7.  **Final Polish**:
    *   Ensure tone is professional and critical.
    *   Cite specific Plan numbers (e.g., "In Plan 01-03...").
    *   Check against the "Locked Design Decisions" constraints provided in the prompt.

    *(Self-Correction)*: Looking at Plan 01-01 Task 2, it checks `grep -E 'json\.dumps'`. Plan 01-02 Task 3 implements the lint. Plan 01-02 Task 1 implements `canonicalize`. The lint script needs to check the new `canonical.py` file. The check command in Task 3 is `grep -E 'json\.dumps' thermocline/python/src/thermocline/ -r...`. This seems correct.

    *(Self-Correction on D-01)*: The prompt emphasizes D-01.
    *Plan 01-03 Task 1* checks `mypy --strict thermocline/python/src/thermocline/identity.py`. It *does* check the misuse fixture. But does it test `dataclasses.replace`? No. Does it test `pickle`? No.
    *Suggestion*: Add `test_receipt_replication` using `copy` and `dataclasses.replace`.

    *(Self-Correction on IDENT-05)*:
    *Plan 01-03 Task 2*:
    `grep -rE 'import (keyring|nacl)' ... | grep identity.py` - checks only identity.py.
    `grep -rE 'os\.environ|os\.getenv|pathlib|open\(' thermocline/python/src/thermocline/identity.py` - ensures file I/O isn't used.
    This is a *very* strong guard. It's MEDIUM risk only if the platform keyring mechanism itself is broken (e.g., macOS update breaking keychain access via python-keyring).

    *(Sensitive Transparency)*:
    Plan 01-01 Task 2 checks `Sensitive[bytes]`.
    Plan 01-03 uses `canonicalize`.
    If I do `Task.model_construct(content=Sensitive[data(b'123'))`, does it print '123' in string representation?
    The plan doesn't explicitly check string representation of a constructed object in Task 01-02 or 01-01.
    However, Plan 01-01 Task 2 checks `grep -E '\.dict\(|\.json\(\)' thermocline/python/src/thermocline/envelope.py`. This attempts to prevent v1-style serialization in the *code* generation, but a model instance might still be printable.
    *Suggestion*: Add a test that creates an object via `model_construct` and checks `.dict()` output or string representation does not leak data.

    *(Dependencies)*:
    Plan 01-02 modifies `pyproject.toml`.
    Plan 01-03 modifies `pyproject.toml`.
    Plan 01-01 modifies `pyproject.toml`.
    These are sequential and additive. Correct.

    *(6 AT-C Fixtures)*:
    They map perfectly to the description in the prompt ("AT-C1..C6 = 6 fixtures").

    *(Conclusion on Risk)*:
    LOW/MEDIUM. The specs are strict. The test harness is rigorous. The only potential issue is the "hard fail" on the keystore which might require configuration steps that CI doesn't automatically satisfy (e.g., MacOS Keychain unlocking).

    *Formatting*: Use the requested markdown structure.
</details>

---

## Consensus Summary

Only one external reviewer was available, so this section synthesizes the single
reviewer's report rather than cross-referencing multiple AI critiques.

### Agreed Strengths
- Strict type-safety discipline: `mypy --strict`, hardcoded grep gates against
  `.dict()` / `.json()` / `json.dumps`, AST-based Pitfall 11 lint.
- Comprehensive negative-test coverage: AT-C1..AT-C6 fixtures with structured
  `expect_error_code` mapping (D-04 manifest schema).
- Public API discipline: `canonicalize` pinned to `rfc8785`, single canonical
  path enforced across the suite.
- Keystore hardening: IDENT-05's startup probe + no-filesystem-fallback grep
  guard meaningfully closes the "convenient fallback" footgun.

### Agreed Concerns

**HIGH — D-01 runtime escape hatches not exhaustively tested.** The current
test set covers direct `Receipt(...)` construction and the static `mypy --strict`
misuse fixture, but does NOT exercise:
- `dataclasses.replace(receipt, envelope_id="x")` — for frozen slotted
  dataclasses this typically raises (`replace` calls `__init__`, which still
  needs the sentinel), but the behavior is not pinned by a test.
- `copy.copy(receipt)` / `copy.deepcopy(receipt)` — these go through
  `__reduce_ex__` / `__copy__` paths that bypass `__init__`.
- `pickle.dumps(receipt)` then `pickle.loads(...)` — same `__reduce_ex__`
  concern, plus subprocess-boundary attacks.
- `Receipt.__init_subclass__` / a subclass that overrides `__init__` to drop
  the sentinel check.

**MEDIUM — IDENT-05 robustness in headless / containerized environments.**
The `NoKeyringError` + backend-name heuristic is good, but `python-keyring`
may register a backend that *appears* viable yet fails on the first
`set_password` call in environments without a D-Bus session (Linux containers),
without `securityd` access (locked macOS Keychain), or in restricted CI
environments. The "refuse to start" rule may be too rigid for valid
deployment targets (AWS Lambda, headless Docker) — this is a tradeoff the
spec demands, but the test surface should explicitly cover headless/locked
keystore states with mocked backends.

**MEDIUM — `Sensitive[T]` wire-transparency under all Pydantic v2 paths.**
Plans 01-01 and 01-02 prove the wrapper round-trips byte-for-byte through
`model_dump(mode="json")` / `model_dump_json()` / Hypothesis property tests.
Not directly covered:
- `model_construct(...)` — bypasses the custom validator/serializer entirely;
  may produce a `ContentBlock` whose `.content` is raw `bytes` rather than
  `Sensitive[bytes]`, and a downstream `repr()` or `model_dump()` could leak.
- `TypeAdapter[ContentBlock]` paths used by FastAPI / external code.
- `copy.deepcopy(envelope)` of an envelope containing `Sensitive[bytes]`.

**LOW — Pitfall 11 lint allowlist completeness.** The AST visitor catches
direct `json.dumps(...)` calls and `json.dump(...)` calls. It does NOT catch:
- Dynamic imports: `getattr(__import__('json'), 'dumps')(...)`.
- Aliased imports: `from json import dumps as _d; _d(...)`.
- Third-party libraries that internally call `json.dumps` (out of scope by
  design, but worth documenting).
- `simplejson.dumps`, `orjson.dumps`, `ujson.dumps` (different non-canonical
  serializers — no test that they're absent).

### Divergent Views

N/A — single reviewer. Re-run \`/gsd-review --phase 1 --all\` after installing
\`gemini\`, \`codex\`, or another non-Anthropic CLI to surface disagreements.

### Suggested Revisions for \`/gsd-plan-phase 1 --reviews\`

If you want these concerns folded into the plans before execution:

1. **Plan 01-03 Task 1** — add tests for `Receipt` immutability under
   `dataclasses.replace`, `copy.copy`, `copy.deepcopy`, `pickle.dumps`/`loads`,
   and a `Receipt` subclass that drops the sentinel.
2. **Plan 01-03 Task 2** — add a test that mocks `keyring.set_password` to
   raise on first call (simulating a backend that registers but doesn't
   function); confirm `BrineProvider.__init__` either succeeds (and the
   later `sign` call surfaces the failure) or, ideally, probes by writing
   a transient sentinel value during `__init__`.
3. **Plan 01-01 Task 2 / Plan 01-02 Task 2** — add a test that
   `Task.model_construct(context=[ContentBlock.model_construct(content=b"raw")])`
   does NOT leak raw bytes through `repr()` / `model_dump()` / canonicalize,
   OR document explicitly that `model_construct` is unsafe and add a CI lint
   forbidding it in library code.
4. **Plan 01-02 Task 3** — extend the `check_no_json_dumps` AST visitor to
   also flag `from json import dumps`, `from simplejson|orjson|ujson import dumps`,
   and dynamic attribute access patterns (`getattr(json, "dumps")`).

These are MEDIUM-priority refinements; the plans as committed already pass
the workflow's coverage gates and the spec contract, so executing as-is and
landing the additional tests as a Phase 4 hardening sweep is also reasonable.
