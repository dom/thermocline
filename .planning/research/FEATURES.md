# Feature Research

**Domain:** Thermocline Suite v0.1 Python reference implementation (envelope spec + shared library + policy engine + forge upgrades)
**Researched:** 2026-05-05
**Confidence:** HIGH (the three specs enumerate the feature set directly; this document categorizes and prioritizes across the suite)

## Feature Landscape

The suite has three layers, each with its own feature surface. We categorize per layer to surface what's table stakes vs. differentiating vs. anti-features at each layer.

### Table Stakes (Users Expect These)

**Thermocline (envelope spec + `thermocline-py` shared library):**

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Envelope types: task / task_result / job / job_result / error | Core spec contract | LOW | Pydantic v2 models; JSON Schema export from same source |
| Canonical JSON serialization for signing input | RFC 8785; required for cross-impl signature verifiability | LOW | Single library call (`rfc8785.canonicalize`) but easy to forget — must be the *only* path used for signature input |
| `IdentityProvider` interface | Thermocline normative role | MEDIUM | Abstract base class with required methods (sign / verify / scheme / generate / public / rotate / revoke); v0.1 implements `generate / public / sign / verify`; `rotate / revoke` deferred but the API exists |
| Brine (ed25519) reference adapter | Thermocline default key scheme | MEDIUM | PyNaCl-based; private key lives in platform keystore via `keyring`; reference adapter never holds keys in process memory |
| JSON Schema artifacts for every envelope shape | Cross-language conformance contract | LOW | Generated from Pydantic models; published under `thermocline/schema/` |
| Conformance fixtures (request/response JSON pairs) | Validates third-party impls | MEDIUM | Library + standalone JSON files |

**Photophore (policy engine):**

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Channel registry with full lifecycle (PROPOSED → OPEN → SUSPENDED → CLOSED) | Spec primary abstraction | MEDIUM | Trust store backed by `python-keyring`; ceiling rules; immutable key scheme per channel |
| Three-tier classification with strict priority order | Spec foundation | MEDIUM | Explicit Tag → Path Rule → Classifier; higher priority always wins |
| Rule-based v0.1 classifier | Spec mandate | MEDIUM | Credentials/PII/sensitive types → local; everything else default local via explicit `default_tier()` |
| Classification explanation API | Spec: every assignment is queryable | LOW | `(tier, reason)` tuple; reason is one of `explicit_tag`, `path_rule:<pattern>`, `classifier:<rule>`, `classifier:default` |
| Dispatch-time shadow generation for `task` envelopes | Spec primary protocol element | HIGH | Per-content-type abstraction strategies per Photophore v0.3 quality table |
| Shadow quality tests (irreversibility hard-fail; relevance + distinguishability soft-warn) | Spec v0.3 mandate | HIGH | Irreversibility test gates dispatch; failures abort |
| `result_policy` authoring on outgoing `task` envelopes | Spec: forge cannot escalate | MEDIUM | Authored from channel ceiling + envelope draft + intent tags; input draft `result_policy` is ignored |
| Privacy receipts: dispatch-sig + receipt-sig round trip | Spec primary contract | MEDIUM | Receipt verification through `IdentityProvider`; type-system enforced gate |
| Append-only cryptographically chained audit log (Ring 1, SQLite) | Spec first-class infrastructure | HIGH | BLAKE3 chain with `algo_version`; SQLite triggers enforce append-only; chain-integrity verification on read |
| Audit log queryability + JSON Lines export + chain-head proof | Spec mandate | MEDIUM | SQL views/indexes; export tool |
| `AnchorTarget` trait/protocol with no-op default | v0.1 ships only the interface; Ring 3 deferred to spec v0.4 | LOW | Python `Protocol` or ABC; no-op impl is the default |
| CLI: `photophore channel | audit | classify | policy | dispatch` | Operability | MEDIUM | `click`-based; JSON output mode for scripting |

**Seamount (forge upgrades):**

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `pi-forge` real `brine` (ed25519) signing/verification | Existing stub becomes real | LOW | Drops in `thermocline-py`; replaces TODO comments in `pi-forge/envelope.py` |
| Second reference forge that exercises tier-1 shadow handling | `pi-forge` is tier-2-only by design — we need at least one demo forge that demonstrates a forge reasoning over a shadow | MEDIUM | Proposed: `describe-forge` — accepts a shadow + relevance and returns a templated description (tier-2 output, deliberately small surface) |
| Cross-suite conformance test harness | Any forge implementation should be runnable through it | MEDIUM | Standalone Python tool that POSTs envelopes, validates responses against schemas, checks receipt signatures |
| Forge conformance checklist verification | Seamount v0.3 normative requirements | LOW | Test harness output maps each requirement to pass/fail |

### Differentiators (Competitive Advantage)

Features unique to the Thermocline Suite that distinguish it from generic policy engines / DLP / API gateways.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Cryptographic chaining of audit log (Ring 1) | Tampering becomes mathematically detectable | MEDIUM | BLAKE3 + previous-entry hash + chain-head export |
| Per-dispatch unique shadow IDs over `os.urandom` | Prevents cross-dispatch correlation (AT-C3 / AT-A2 mitigation) | LOW | UUIDv4 over OsRng or `secrets.token_hex` |
| Three-ring storage model (local → shared → blockchain) | Same record at escalating provenance | HIGH | v0.1 ships Ring 1 + Ring 3 *hook only* |
| Issuer-authored result policy that forge cannot escalate | Inverts normal client-server trust | MEDIUM | Already in table stakes; calling out vs. typical API gateway patterns |
| Channel-scoped immutable key scheme | Prevents downgrade attacks during channel lifetime | LOW | Verifier dispatches on `channel.key_scheme`; mismatched-scheme envelopes rejected |
| Identity Provider role separation (Photophore + forge never hold keys) | Eliminates key-exfiltration surface from policy engine | MEDIUM | `thermocline-py` reference adapter calls keystore per signature |
| Type-enforced receipt verification gate (`Receipt` constructible only via `verify`) | "Skipped verification" cannot be expressed in code | LOW | Pydantic model with private constructor pattern |

### Anti-Features (Commonly Requested, Often Problematic)

Features that look reasonable but contradict foundational premises of the spec.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-trust escalation on "good behavior" | "Tedious to keep raising ceilings manually" | Violates Photophore Design Constraint 2 — trust is always a human act | Surface trust-score *suggestions*; user always decides. Make CLI prompts low-friction. |
| Cloud-hosted classifier ("just call OpenAI") | Higher accuracy, no local model burden | Direct violation of sovereign-node principle | v0.1 rule classifier; v0.3 local model only |
| Caching shadows for performance | "Don't regenerate the same shadow twice" | Defeats per-dispatch shadow-ID uniqueness; AT-C3 / AT-A2 attack viable | Cache classification *result*, not shadow itself |
| Eager classification at content-write time | "Index everything once so dispatch is fast" | Spec mandates dispatch-time classification | Run path-rule pre-pass at write time as a *hint*; final classification at dispatch |
| Co-locating trust store with audit log in one SQLite | "One database is simpler" | AT-A5 mitigation depends on separate stores | Trust store in platform keystore; audit log in SQLite. Always |
| Trust store cloud sync ("for backup") | DR convenience | Spec mandate: trust store never leaves the node | Document a manual encrypt-and-export procedure user invokes |
| Automatic key rotation without user signal | "Best practice" | Silent rotation breaks audit-log interpretability | Scheduled prompts; user-confirmed rotation in audit log |
| Permissive default tier ("nothing important here") | Easier onboarding | Privacy guarantee depends on `local` default | Onboarding UX explains the default and walks through tag/rule setup |
| Audit log delete/edit APIs ("GDPR right to be forgotten") | Compliance optics | Audit log is the proof; deleting destroys it | Archive-and-restart pattern; archives remain. Audit records *that* a dispatch happened, not *what content* was — content lives in originating store, deletable |
| Resumable jobs in `pi-forge` or any v0.1 forge | "Why throw away partial work" | Thermocline Job Integrity Rule: halted job is dead | Issuer reissues with new `job_id` |
| Persistent forge cache of prior envelopes | "Speed up repeated requests" | Violates Seamount statelessness mandate | Forge holds nothing across requests, ever |
| `print()`-based debugging in library code | Quick to add | Leaks tier-0 content to stdout in unpredictable contexts | `logging` with a redacting filter; CI lint forbids `print()` in `thermocline/` and `photophore/` library code |

## Feature Dependencies

```
[Thermocline-py shared library]
        │
        ├──provides──> Envelope types (Pydantic)
        ├──provides──> Canonical JSON
        ├──provides──> IdentityProvider interface + brine adapter
        └──provides──> JSON Schema artifacts
                                                        │
[Photophore Channel Store]                              │
        ├──depends on──> python-keyring (platform store)│
        ├──depends on──> Audit Log (writes lifecycle events)
        └──used by──> Dispatch Coordinator              │
                                                        │
[Photophore Classifier]                                 │
        ├──depends on──> Path Rule Engine               │
        └──depends on──> Explicit Tag Parser            │
                                                        │
[Photophore Shadow Generator]                           │
        ├──consumes──> Classifier output (tier=1 blocks)│
        └──depends on──> Shadow Quality Tests           │
                                                        │
[Photophore Result Policy Authoring]                    │
        └──reads──> Channel ceiling + envelope draft    │
                                                        │
[Photophore Audit Log]                                  │
        ├──written by──> EVERY operation across the engine
        └──reads──> Chain integrity verification on query
                                                        │
[Photophore Dispatch Coordinator]                       │
        ├──orchestrates──> Channel + Classifier + Shadow + Policy + IdP + Audit
        └──uses──> thermocline-py for envelope serialization + signing
                                                        │
[pi-forge upgrade]                                      │
        └──depends on──> thermocline-py (replaces brine stubs)
                                                        │
[describe-forge (new tier-1 demo forge)]                │
        ├──depends on──> thermocline-py                 │
        └──exercises──> Tier-1 shadow handling end-to-end
                                                        │
[Conformance Test Harness]                              │
        ├──depends on──> thermocline-py JSON Schema artifacts
        └──runs against──> Any forge implementation
```

### Dependency Notes

- **`thermocline-py` is the foundation.** Every other component depends on it. It must land in Phase 1 before anything else can.
- **Photophore Audit Log writes from everywhere.** Implementing the audit primitive early in Phase 2 (immediately after `thermocline-py`) means every later component can audit-log without coordination overhead.
- **Photophore Classifier and Shadow Generator are pure (no I/O).** They can be developed and unit-tested without Audit or IdP available — but the audit primitive should exist by then so dispatch (Phase 3) can wire them together.
- **`pi-forge` upgrade is a small, satisfying milestone.** Once `thermocline-py` exists, replacing the stubs is a few hundred lines. Pair it with the new `describe-forge` so we have at least one tier-1-exercising integration test.
- **The conformance test harness is the proof point.** It validates third-party forges and is itself a deliverable that proves the spec is implementable.

## MVP Definition

### Launch With (v0.1 of this milestone)

**Thermocline:**
- Spec patches as discovered during impl (one already landed: cirdan→thermocline)
- JSON Schema artifacts for every envelope shape
- `thermocline-py` library: envelope types, canonical JSON, brine adapter, IdP interface, conformance fixtures

**Photophore:**
- Channel registry + lifecycle + platform keystore backing
- Three-tier classification + path rule engine + rule-based v0.1 classifier + explanation API
- Shadow generator + per-content-type abstraction strategies + three quality tests
- `result_policy` authoring on `task` envelopes
- Append-only chained audit log (SQLite + BLAKE3 + `algo_version`)
- Privacy receipts (dispatch + receipt sig verification through `thermocline-py`)
- Dispatch coordinator (9-step flow, async, network-isolated)
- Anchoring hook (interface only — no-op default)
- CLI

**Seamount:**
- `pi-forge` real brine via `thermocline-py`
- `describe-forge` (or named alternative) — second reference forge exercising tier-1 shadows
- Cross-suite conformance test harness

**Suite-wide:**
- End-to-end integration test (Photophore → upgraded `pi-forge` and `describe-forge` → verified receipts → audit-log entries)
- Three coordinated v0.1 git tags

### Add After Validation (v0.2 of the suite milestone — not v0.2 of the *specs*)

- Per-step shadow generation for `job` envelopes (Photophore + Seamount + thermocline-py changes; spec already covers v0.2 of Photophore)
- A second tier-2 forge variant (e.g., a small text-summarization forge) to validate task routing in Seamount
- TypeScript client library `thermocline-ts` (cross-language conformance proof)

### Future Consideration (later milestones)

- Trust score algorithm (Photophore spec v0.3)
- Model-based classifier (Photophore spec v0.3, opt-in, local-only)
- Multi-hop channels (Photophore spec v0.4)
- Ring 3 / Arweave anchor (Photophore spec v0.4)
- Channel negotiation protocol (Photophore spec v1.0)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `thermocline-py` envelope types + canonical JSON | HIGH | LOW | P1 |
| `thermocline-py` brine adapter + IdP interface | HIGH | MEDIUM | P1 |
| JSON Schema artifacts | HIGH | LOW | P1 |
| Photophore audit log (chained, SQLite) | HIGH | HIGH | P1 |
| Photophore channel registry + trust store | HIGH | MEDIUM | P1 |
| Three-tier classifier with priority order | HIGH | MEDIUM | P1 |
| Shadow generator + quality tests | HIGH | HIGH | P1 |
| Photophore result_policy authoring | HIGH | MEDIUM | P1 |
| Photophore dispatch coordinator | HIGH | MEDIUM | P1 |
| `pi-forge` real brine | HIGH | LOW | P1 |
| `describe-forge` (tier-1 demo forge) | HIGH | MEDIUM | P1 |
| Conformance test harness | HIGH | MEDIUM | P1 |
| Per-step job shadow generation | HIGH | HIGH | P2 (future milestone) |
| Trust score algorithm | MEDIUM | HIGH | P2 (future milestone) |
| Model-based classifier | MEDIUM | HIGH | P3 (future milestone) |
| Ring 2 / Ring 3 implementations | MEDIUM | HIGH | P3 (future milestone) |

## Sources

- Specs: `thermocline/README.md`, `photophore/README.md`, `seamount/README.md` — all v0.3.0-draft
- Existing reference: `seamount/pi-forge/` — Python 3.11 / Flask / mpmath
- Confidence: HIGH on the v0.1 feature list (drawn from spec roadmaps); MEDIUM on the prioritization (our judgment)

---
*Feature research for: Thermocline Suite v0.1*
*Researched: 2026-05-05*
