# Pitfalls Research

**Domain:** Thermocline Suite v0.1 Python reference implementation
**Researched:** 2026-05-05
**Confidence:** HIGH (drawn from the three specs' threat models — Thermocline AT-C1..C6, Photophore AT-A1..A6, Seamount AT-E1..E5 — plus Python-specific failure modes)

## Critical Pitfalls

### Pitfall 1: Classifier Default Drift

**What goes wrong:** A maintainer adds a new content type or rule, and the implicit "everything else" branch ends up assigning `shared` or `public` to content that should be `local`.
**Why it happens:** Conservative default is easy to forget in code review. Python's `match` and `if/elif/else` branches don't enforce exhaustive handling.
**How to avoid:**
- Make `Tier.LOCAL` the value returned by an explicit `default_tier()` function. Classifier MUST call this, not return a literal.
- Property test (Hypothesis): for any `ContentBlock` with no explicit tag and no path-rule match, `classify(block, rules) == Classification(Tier.LOCAL, Reason.CLASSIFIER_DEFAULT)`.
- CI lint: `Tier.PUBLIC` and `Tier.SHARED` may not appear in `photophore/classifier.py` outside the explicit-tag and path-rule handlers.
**Phase to address:** Phase 2 (classifier) — the property test must land with the classifier merge.

### Pitfall 2: Shadow Abstraction Leakage

**What goes wrong:** A shadow's `abstraction` string passes the schema (string, reasonable length) but contains identifying detail like "a Q3 earnings memo from a Bay Area technology company".
**Why it happens:** Optimizing for relevance preservation while forgetting the irreversibility test.
**How to avoid:**
- `irreversibility_test(shadow) -> None` runs heuristic checks: no proper nouns, no specific dates, no organization tokens, length within fixed budget per type. Hard fail on any check.
- Maintain a `tests/fixtures/leaky_abstractions/` directory of caught regressions.
- Run the test as a hard gate in `dispatch.dispatch` — failure aborts the dispatch.
**Phase to address:** Phase 2 (shadow generator).

### Pitfall 3: Audit Chain Algorithm Lock-In

**What goes wrong:** The chain hash algorithm is hardcoded in entry struct/JSON without versioning. Years later, vulnerability or interop need forces migration that the immutable chain can't accommodate.
**Why it happens:** "YAGNI" — version fields feel premature with one algorithm.
**How to avoid:**
- Include `algo_version: str = "blake3-v1"` in every audit entry from day 1.
- Verifier dispatches on `algo_version` and raises `UnsupportedChainAlgoError` for unknown values.
- v0.1 implements only `blake3-v1`; the dispatch path exists.
**Phase to address:** Phase 2 (audit log schema).

### Pitfall 4: Implicit Trust Elevation Through "Helpful" Logging

**What goes wrong:** A `logger.info("dispatching: %s", envelope)` writes tier-0 content to a log file that gets shipped to a log aggregator.
**Why it happens:** Python's `__repr__` is reflexive; `BaseModel.__repr__` includes every field; `logger.info("...%s...", thing)` calls `repr(thing)`.
**How to avoid:**
- `Sensitive[T]` wrapper class with redacting `__repr__`/`__str__`.
- Pydantic config `arbitrary_types_allowed=True`; envelope content fields typed as `Sensitive[bytes]`.
- CI lint: `print(` is forbidden in `thermocline/src/` and `photophore/src/`. `logger.*` calls that include un-wrapped `ContentBlock`/envelope variables flagged in code review.
- Add a `logging.Filter` that drops fields tagged `sensitive=True`.
**Phase to address:** Phase 1 (`thermocline.envelope` types — establish the discipline up front).

### Pitfall 5: Receipt Verification Skipped Under Time Pressure

**What goes wrong:** The dispatch coordinator audit-logs a "receipt" before verifying the signature. Forged receipts produce false "successful" audit records.
**Why it happens:** Async error handling is easy to short-circuit; "verify later" feels like a tempting refactor.
**How to avoid:**
- `Receipt` constructible only by `IdentityProvider.verify()` returning success — there's no public constructor.
- `dispatch.dispatch` calls `verify` *before* any audit write referencing the receipt.
- Integration test: forge stub returns malformed signature; assert `DispatchError.RECEIPT_INVALID` and audit log contains no receipt entry for that dispatch.
**Phase to address:** Phase 3 (dispatch coordinator).

### Pitfall 6: Trust Store Backup That Defeats the Threat Model

**What goes wrong:** "Convenience" backup feature exports trust store to a file or to remote storage; the file becomes the new attack surface.
**Why it happens:** Operational pressure ("what if my Mac dies?"), borrowed expectations from password-manager UX.
**How to avoid:**
- Follow the spec literally: trust store NEVER leaves the node, no remote sync.
- Document the manual recovery procedure: re-establish channels with remote nodes (re-establishment is a *feature* — fresh trust attestation).
- Spec-compliance review for any PR titled "trust store backup" before code review.
**Phase to address:** Phase 2 (`photophore.channels`).

### Pitfall 7: Eager Classification at Write Time Instead of Dispatch Time

**What goes wrong:** Classify when content is written, then cache the result. Cache becomes stale; cached `shared` classification reused across channels with different ceilings; private content leaks to the lower-ceiling channel.
**Why it happens:** "Classification is expensive; let's amortize it" is a natural systems-engineering instinct.
**How to avoid:**
- Spec compliance: classification runs every dispatch.
- Cache *path-rule lookups* (cheap, channel-independent) but NOT classification *results*.
- Test: dispatch the same content twice in quick succession, assert audit log shows two classification reasons and shadow IDs are different.
**Phase to address:** Phase 3 (dispatch coordinator) — ADR forbidding cross-dispatch classification cache.

### Pitfall 8: Insufficient Path-Rule Catch-All Validation

**What goes wrong:** A user's path-rules YAML is missing the mandatory `**` → `local` catch-all. Photophore loads without complaint; unmatched content gets undefined tier.
**Why it happens:** YAML parsers don't enforce semantic rules; the catch-all mandate is in spec prose, not schema.
**How to avoid:**
- Validate path-rules config at load time. Reject any config that lacks an exact `**` → `local` entry as the LAST rule.
- `photophore config validate` CLI command runs at startup; refuse to start if invalid.
- Provide a default config template; document that removing the catch-all is unsupported.
**Phase to address:** Phase 2 (classifier).

### Pitfall 9: Identity Provider Adapter That Holds Keys In Process

**What goes wrong:** "Convenient" adapter decrypts the private key into process memory at startup and signs in-process. Photophore's process memory now contains key material — threat model assumed it would not.
**Why it happens:** Performance optimization; "we'll fix later"; misreading "delegate signing" as "import key".
**How to avoid:**
- Reference adapter calls `python-keyring` for *every signature*. Keystore returns a signature, never the key.
- The `IdentityProvider.sign` Protocol returns `Signature`, never `PrivateKey`. Adapter cannot violate the contract by accident.
- Apple Silicon Secure Enclave entries cannot be exported even if requested — leverage when available.
**Phase to address:** Phase 1 (`thermocline.identity`).

### Pitfall 10: Conformance Tests That Don't Test Negatives

**What goes wrong:** Tests verify valid envelopes round-trip. They don't verify that *invalid* envelopes are rejected (forged signatures, mismatched key schemes, missing result_policy, escalated tiers).
**Why it happens:** Happy-path testing is faster to write.
**How to avoid:**
- For each AT-* surface (Thermocline AT-C1..C6, Photophore AT-A1..A6, Seamount AT-E1..E5), at least one negative test.
- Maintain `tests/invalid/` fixtures, each documenting the surface it exercises.
- CI: count negative tests by AT-* surface; fail if any surface has zero coverage.
**Phase to address:** Phase 4 (conformance suite).

### Pitfall 11: `json.dumps` for Signing Input (Python-specific)

**What goes wrong:** Using `json.dumps(envelope.model_dump())` to compute signing bytes. Python's default JSON output is non-canonical (sort_keys default is False, separators have spaces). A signature computed over one Python's output may not verify on another runtime.
**Why it happens:** It's the obvious code; canonical JSON is a separate library most Python devs haven't used.
**How to avoid:**
- Single canonical path: `thermocline.canonical.canonicalize(model.model_dump(mode='json'))` returns `bytes`. All signing/verifying uses this.
- Property test (Hypothesis): for any envelope, `canonicalize(envelope) == canonicalize(deserialize(serialize(envelope)))`.
- CI lint: `json.dumps(` flagged in `thermocline/src/` and `photophore/src/` outside of explicitly non-signing paths.
**Phase to address:** Phase 1 (`thermocline.canonical`).

### Pitfall 12: Pydantic v1 vs v2 Serialization Differences (Python-specific)

**What goes wrong:** Code uses Pydantic v1 patterns (`.dict()`, `.json()`) where v2 has changed behavior (`.model_dump()`, `.model_dump_json()`). Mixed-version codebase produces subtly different envelope JSON, breaking signatures.
**Why it happens:** Many Python tutorials still show v1 patterns; copy-paste from old code.
**How to avoid:**
- Pin `pydantic>=2.7,<3.0` in every `pyproject.toml`.
- CI lint: `\.dict\(` and `\.json\(\)` flagged in any package.
- Use `model_dump(mode="json")` consistently for serialization; document in CONTRIBUTING.
**Phase to address:** Phase 1 (`thermocline-py`).

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded `algo_version="blake3-v1"` without versioned dispatch | Less code | Cannot migrate hash; one-line decision determines forever-properties | Never |
| Skipping irreversibility test "for now" | Ships shadows faster | Privacy violation by default | Never — irreversibility is hard constraint |
| Single SQLite for trust store + audit log | Simpler ops | Conflates threat boundaries | Never |
| `raise Exception` instead of specific subclass | Shorter code | Callers can't distinguish; error-handling regresses | Only in tests with explicit `pytest.raises(Exception)` |
| Caching identity-provider unlock state | Avoids biometric prompt fatigue | Breaks delegation guarantee | v0.5+ with explicit user opt-in and audit-log entries; never v0.1 |
| Skipping shadow distinguishability test (warn only) | Faster dispatch on edge cases | Lower-quality shadows; eventual privacy regression | Acceptable in v0.1 if test runs and warns; never if test removed |
| Ed25519 only, no scheme abstraction | Less indirection | Future migration to PQ signatures requires a rewrite | Acceptable in v0.1 IF `channel.key_scheme` is in the data model and verifier dispatches on it |
| `json.dumps` for signing input "it's deterministic enough" | One fewer dependency | Signature breaks with map-ordering or whitespace changes | Never |
| Pydantic v1 `.dict()` patterns "they still work" | Avoids migration cost | Drift to non-canonical serialization across modules | Never — Pydantic v2 only |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| macOS Keychain via `python-keyring` | Storing entries that require biometric unlock without prompting infrastructure | Detect biometric requirement at channel-open time; surface a CLI prompt ("Touch ID required to access Keychain entry") |
| Apple Silicon Secure Enclave | Assuming `python-keyring` transparently uses Secure Enclave | Verify entry attributes; may need direct `pyobjc` calls for SE-specific entries |
| Linux `libsecret` | Failing on headless servers (no D-Bus session) | Detect at startup; refuse to run rather than silent file fallback |
| Windows Credential Manager | UTF-8 vs UTF-16 string handling | `python-keyring` handles this, but custom integrations historically don't. Test with non-ASCII channel names |
| SQLite WAL mode | Forgetting to checkpoint; WAL grows indefinitely | `PRAGMA wal_autocheckpoint=1000`; manual checkpoint on graceful shutdown |
| Thermocline envelope schema | Implementing an older envelope shape (e.g., `cirdan` field) | Pin to `thermocline>=0.3.1`; CI conformance run against canonical fixtures |
| Tokio + blocking SQLite (Python equivalent: asyncio + sync sqlite3) | Calling `sqlite3` directly in async functions | Wrap in `asyncio.to_thread` or use `aiosqlite` |
| Flask in `pi-forge` | Synchronous Flask blocks under concurrent requests | Acceptable for v0.1 forge (low rate); Gunicorn + workers for any production-like deploy |
| `httpx` certificate validation | Disabling for local testing leaks into production | Use `verify=False` only via `--insecure` CLI flag with audit-log warning; never default |
| `python-keyring` collection vs. service | Storing channels under different "service" names is confusing | Single service name `photophore` for all entries; entry name encodes channel ID |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Recomputing path-rule matches per content block | Slow classification on dispatches with many blocks | Compile rules into `aho-corasick` or precomputed glob set at config load | Bursts of >100 blocks per dispatch |
| BLAKE3 chain-hash on full audit log on every read | Linear-time chain verification grows with log size | Verify only the slice of entries returned by query; expose chain-head verification as separate explicit op | After ~10k audit entries |
| SQLite WAL bloat | Disk usage grows unboundedly | Periodic `wal_checkpoint(TRUNCATE)`; document in ops guide | Long-running dispatches on busy node |
| Synchronous keystore RPC on every audit-log write | Latency spikes on audit | Audit writes don't need keystore — only signing does | Refactors that "unify" signing and audit |
| Pydantic v2 model creation in tight classification loops | CPU bound under load | Cache `ContentBlock.model_validate` precompiled validators where possible; avoid re-parsing JSON multiple times | Only on extremely high dispatch rates — likely premature for v0.1 |
| Flask single-threaded forge under concurrent test load | 503s during conformance harness runs | `gunicorn -w 4` for any concurrent test; document for ops | Test runs with parallel workers |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging signed envelope bytes after signing | Signature material leaks | Wrap envelope post-sign in `Sensitive`; redact in logs |
| Using `random.random` for shadow IDs | Predictable IDs → AT-C3 / AT-A2 viable | `secrets.token_hex(16)` always; never `random` module |
| Failing closed → failing open on transient errors | Audit RPC timeout returns success | Audit failures are dispatch failures. No optimistic paths |
| Using `==` to compare signatures (timing oracle) | Side-channel timing attacks | Use `nacl.signing.VerifyKey.verify` (constant-time) — never compare signature bytes by hand |
| Writing partial canonical JSON before signing | Canonicalization bug → signature verifies on receiver but doesn't actually cover full envelope | `thermocline.canonical.canonicalize` is one library call; property-test over arbitrary envelope shapes |
| Hardcoding `key_scheme = "brine"` in verifier | Future channels with different schemes silently downgrade | Verifier dispatches on `channel.key_scheme`; hardcoded values are CI lint failure |
| Allowing user to suppress quality-test failures | User-induced privacy violation | Hard fails non-suppressible; warns suppressible only with audit-log annotation |
| `pickle` anywhere in the suite | Massive deserialization vulnerability | Forbidden; CI lint flags `import pickle` |
| `eval` / `exec` in user-controlled paths | RCE | Forbidden; CI lint flags |
| Loading YAML with `yaml.load` (no safe loader) | RCE via YAML tag exploitation | `yaml.safe_load` only; CI lint flags `yaml.load(` without `Loader=` |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Cryptic "tier mismatch" errors | User can't diagnose | Errors include classification reason: "Block 3 classified as `local` (reason: classifier:credential_pattern); ceiling on channel 'forge-1' is `tier-1`. Cannot dispatch tier-0 content." |
| No way to ask "why is this `local`?" without dispatching | Over- or under-tagging | `photophore classify <path>` dry-run with full reason output |
| Channel-creation requiring JSON editing | Adoption friction | First-class `photophore channel new` with prompts |
| Trust-score warnings without recommended action | User dismisses | Each threshold band ships with action: "RECOMMEND suspension; run `photophore channel suspend CH123`" |
| Audit query overwhelming raw rows | Can't find the dispatch | Default `--format=summary` (one line per dispatch); offer `--format=json|detail` |
| Silent biometric prompts that look like the app froze | User retries, double-dispatch | Print "Awaiting Keychain unlock..." before initiating |
| Mixing forge URLs in error messages with channel info | User can't tell which channel routed where | Errors include `channel_id`, `forge_url`, `envelope_id` — three keys for diagnosis |

## "Looks Done But Isn't" Checklist

- [ ] **Classifier:** explicit-tag and path-rule branches produce `Reason.EXPLICIT_TAG` / `Reason.path_rule(pattern)` in the assignment record — verify both `tier` AND `reason` round-trip through audit
- [ ] **Shadow generator:** every shadow runs the irreversibility test; failure is a hard error, not a warn — verify with a fixture with intentionally leaky abstraction
- [ ] **Audit log:** chain verification on read covers entire returned slice; refuses to return entries whose `prev_hash` doesn't match — verify with a fixture that tampers a single entry's bytes
- [ ] **Identity provider adapter:** `IdentityProvider.sign` never returns the key; refuses to sign for a scheme other than the channel's declared scheme — verify via Protocol AND runtime check
- [ ] **Dispatch coordinator:** receipt verification happens before the receipt is appended to audit; failure aborts dispatch — verify with a stub forge that returns a forged signature
- [ ] **Trust store:** writing is a single function `Channels.open_channel(...)`, no path mutates outside that function — verify by code search for direct `keyring.set_password` calls
- [ ] **Path rules:** loading a config without `**` → `local` catch-all returns an error before applying — verify with a fixture missing the catch-all
- [ ] **Result policy:** dispatch coordinator authors `result_policy` from channel + draft; never from input — verify by code review and a fixture that includes a draft `result_policy` (must be ignored or rejected)
- [ ] **CLI:** every subcommand emits an audit log entry on completion (success or failure) — verify by integration test grep over audit DB
- [ ] **Anchoring hook:** Protocol exists, no-op default ships, dispatch flow can be configured with no-op without warnings — verify via smoke test
- [ ] **Canonical JSON:** all signing input goes through `thermocline.canonical.canonicalize`; never `json.dumps` — verify by code search and property test
- [ ] **Pydantic v2:** no `.dict()` or v1 patterns anywhere — verify by CI lint
- [ ] **`pi-forge`:** `key_scheme="brine"` works end-to-end with real signing — verify by integration test (not just unit test)
- [ ] **`describe-forge`:** accepts a tier-1 shadow input and produces a tier-2 templated description — verify by an end-to-end Photophore → describe-forge dispatch
- [ ] **Conformance harness:** runs against `pi-forge`, `describe-forge`, and produces structured pass/fail reports against the Seamount conformance checklist — verify by running it as part of CI

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Audit chain corruption detected | MEDIUM | 1. Halt dispatches. 2. Archive corrupted chain (DO NOT delete). 3. Run forensic verification report. 4. Start new chain rooted at the report's hash. 5. Document in audit-archive metadata. |
| Trust store entry tampered | HIGH | 1. Suspend channels backed by tampered entry. 2. Audit-log suspension. 3. Re-establish channels with remote parties. 4. Open security incident ADR. |
| Shadow leakage discovered post-dispatch | HIGH | The bell can't be unrung. 1. Suspend channel. 2. Notify operator. 3. Update abstraction strategy. 4. Add irreversibility-test fixture. 5. Audit-log incident. |
| Receipt verification regressed (CI miss) | LOW (caught early) / HIGH (caught late) | Pre-release: fix forward, add negative test, ship. Post-release: yank if late-caught; communicate to channel operators. |
| Identity adapter accidentally cached keys | HIGH | 1. Treat keys as compromised. 2. Rotate via platform keystore. 3. Re-sign active envelopes (human-confirmed). 4. Patch and rebuild. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Classifier default drift | Phase 2 (classifier) | Hypothesis property test asserts `LOCAL` default |
| Shadow abstraction leakage | Phase 2 (shadow) | Irreversibility test gates dispatch |
| Audit chain algo lock-in | Phase 2 (audit log schema) | `algo_version` field present from day 1 |
| Implicit trust elevation via logging | Phase 1 (`thermocline-py` types) | `Sensitive` wrapper + lint |
| Receipt verification skipped | Phase 3 (dispatch) | `Receipt` constructible only via `verify`; integration test |
| Trust store backup defeating threat model | Phase 2 (channels) | Spec-compliance review; ADR forbids |
| Eager classification at write time | Phase 3 (dispatch) | ADR forbids cross-dispatch classification cache |
| Path-rule catch-all missing | Phase 2 (classifier) | Validation gate at config load |
| Identity provider holding keys | Phase 1 (`thermocline.identity`) | Protocol returns Signature only; per-sign keystore call |
| Negative tests missing | Phase 4 (conformance) | CI gate counts AT-* coverage |
| `json.dumps` for signing | Phase 1 (`thermocline.canonical`) | Single canonical path; lint and property test |
| Pydantic v2 drift | Phase 1 (`thermocline-py`) | CI lint forbids v1 patterns |

## Sources

- Specs: `thermocline/README.md` (Threat Model AT-C1..C6), `photophore/README.md` (Threat Model AT-A1..A6, Design Constraints 1-10), `seamount/README.md` (Threat Model AT-E1..E5)
- Practical privacy-engineering experience patterns from differential privacy, DLP, and OPA retrospectives
- Python idioms: Pydantic v2 docs, `secrets` module docs, `python-keyring` docs
- Confidence: HIGH — these pitfalls are direct mappings from the specs' threat models plus Python-specific failure modes from the existing pi-forge code

---
*Pitfalls research for: Thermocline Suite v0.1 Python reference implementation*
*Researched: 2026-05-05*
