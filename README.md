# Thermocline

### A Privacy-Tiered Task Envelope Specification for Distributed AI Nodes

**Version:** 0.4.0
**Status:** RFC (pre-release, seeking feedback)
**License:** MIT
**Companion Specifications:** Photophore 0.4.0+ (policy engine) · Seamount 0.4.0+ (compute forge)
**Changelog:** [thermocline/CHANGELOG.md](thermocline/CHANGELOG.md) (spec patches discovered during reference-implementation work)

---

## The Problem

Modern AI agent systems treat all context as equally accessible. A task dispatched to
a remote model, a cloud API, or a second machine carries everything (file contents,
personal details, prior conversation, identity signals) because there is no standard
way to say: *this part crosses the boundary, this part does not.*

Existing memory systems (Vertex AI Memory Bank, OpenViking, Mem0, and others) solve
retrieval and persistence well. None of them define a **privacy boundary primitive**.
It is a standard way to strip, abstract, or shadow sensitive context before it leaves a
trusted node, and to reconstruct meaning on the other side without ever transmitting
the original.

This is the gap Thermocline addresses.

---

## What Thermocline Is

Thermocline is a **minimal, transport-agnostic envelope specification** for AI task
dispatch across privacy boundaries.

It defines:

- A **task payload schema** (what a unit of work looks like)
- A **job payload schema** (what a multi-step, manifest-driven unit of work looks like)
- A **privacy tier system** (how context is classified before dispatch)
- A **shadow block** (the abstracted, safe-to-transmit representation of private context)
- A **result schema** (what comes back, and what is permitted to persist)
- A **provenance record** (a lightweight audit trail of what crossed which boundary)
- A **role architecture** (what capabilities a node must have, independent of which system provides them)
- An **identity provider interface** (what the signing system must do, independent of implementation)

Thermocline does **not** define:

- Transport (any of HTTP, WebSocket, local socket, Thunderbolt bridge, or internet)
- Storage (implementor's choice of OpenBrain, SQLite, or flat files)
- Inference (any model, any runtime)
- Policy (who decides what is private is the policy engine's job)

A **forge** is any Thermocline-compliant node that receives task or job envelopes, performs
work, and returns signed results. A forge may be a local desktop machine, a remote
GPU server, a cloud API endpoint, or any other compute resource. See the Seamount
specification for the reference forge implementation and conformance requirements.

Thermocline is the contract. Others implement against it.

---

## Role Architecture

Thermocline defines five functional roles. These are **roles**, not systems. A single
machine may play all five simultaneously. Two instances of the same software on
different machines play different roles.

| Role | Responsibility | May be provided by |
|------|---------------|--------------------|
| **Sovereign Node** | Holds private context, owns the trust root, initiates dispatch | Any system with local storage and user trust |
| **Policy Engine** | Classifies content, generates shadows, authors result policy, signs envelopes | Photophore, or any compliant membrane implementation |
| **Identity Provider** | Generates and manages node keys, signs and verifies envelopes | Any system with secure keystore access (see Identity Provider Interface) |
| **Forge** | Receives envelopes, executes work, returns signed results, holds nothing | Seamount, or any system meeting forge conformance (see Seamount spec) |
| **Memory Store** | Persists results per result_policy after receipt | OpenBrain, or any persistent store |

**Role composition examples:**

A personal laptop running a capable agent system acts as sovereign node, policy
engine, identity provider, and memory store simultaneously. It dispatches to a
desktop forge over a local link.

A cloud GPU instance acts as forge only. It receives envelopes, runs inference,
returns results, and holds nothing between sessions.

Two instances of the same agent system on different machines: one is the sovereign
node (holding private context), the other is the forge (executing work). The
software is identical; the roles are different because the trust relationship is
different.

A mobile device acts as sovereign node and identity provider. A desktop handles
policy engine and forge roles. The split depends on compute capability, not on
which software is installed.

---

## Core Concepts

### Privacy Tiers

Every piece of context in a Thermocline envelope carries one of three tiers:

| Tier | Name | Meaning |
|------|------|---------|
| 0 | `local` | Never leaves the originating node. Not transmitted. |
| 1 | `shared` | May leave the node as a shadow. Raw content stays local. |
| 2 | `public` | Transmitted as-is. No restriction. |

A `local` context block is **never included in dispatch**. Its existence may be
acknowledged (a shadow may reference it), but its contents are never transmitted.

A `shared` context block is **replaced by a shadow** before dispatch. The shadow is
a policy-generated abstraction (a summary, a type hint, an anonymized descriptor)
that conveys relevance without conveying content.

A `public` context block is **transmitted directly**.

### The Shadow

A shadow is the safe representation of a `shared` context block. It is generated by
the policy engine on the originating node before dispatch.

A shadow carries:

- A shadow ID (opaque, locally meaningful, not reversible)
- A content type hint (`file`, `conversation`, `identity`, `credential`, `document`, etc.)
- An abstraction string (a human-readable description with no identifying detail)
- A relevance score (0.0–1.0) indicating how pertinent this context is to the task

A shadow does **not** carry:

- File contents
- Names, identifiers, or locations unless explicitly public
- Anything that could reconstruct the original

The receiving node uses the shadow to understand *that* context exists and *roughly what
kind* it is, so it can reason appropriately, without ever seeing the source.

### The Task Envelope

The unit of single-dispatch work. Everything the receiving node needs to do the work,
with nothing it shouldn't have.

### The Job Envelope

The unit of multi-step work. A manifest authored on the policy node defines the full
intent, constraints, and step chain before dispatch. The forge executes against the
manifest and never interprets or extends it.

### The Result

What comes back. Thermocline defines which fields in a result are permitted to be persisted
to shared memory vs. returned only to the originating node.

---

## Schema

All Thermocline envelopes are JSON. The schema is intentionally minimal.

---

### Task Envelope

```json
{
  "thermocline": "0.3.0",
  "type": "task",
  "envelope_id": "<uuid>",
  "issued_at": "<iso8601>",
  "issuer": "<node_id>",
  "channel_id": "<channel>",
  "task": {
    "type": "<task_type>",
    "instruction": "<natural language or structured prompt>",
    "parameters": {}
  },
  "context": [
    {
      "tier": 2,
      "role": "system_background",
      "content": "<public context transmitted as-is>"
    },
    {
      "tier": 1,
      "role": "user_file",
      "shadow": {
        "shadow_id": "<opaque_id>",
        "content_type": "document",
        "abstraction": "A personal financial summary document from 2024",
        "relevance": 0.85
      }
    }
  ],
  "result_policy": {
    "persist_to_shared": ["summary", "artifacts"],
    "return_only": ["raw_output"],
    "strip_before_persist": ["pii", "file_references"]
  },
  "dispatch_signature": {
    "key_scheme": "brine",
    "node_id": "<issuer>",
    "channel_id": "<channel>",
    "policy_hash": "<hash of policy applied>",
    "shadows_generated": ["<shadow_id>", "..."],
    "timestamp": "<iso8601>",
    "sig": "<signature over canonical envelope>"
  }
}
```

### Task Result Envelope

```json
{
  "thermocline": "0.3.0",
  "type": "task_result",
  "envelope_id": "<matches task envelope_id>",
  "result_id": "<uuid>",
  "completed_at": "<iso8601>",
  "responder": "<node_id>",
  "outputs": {
    "summary": "<safe to persist per result_policy>",
    "artifacts": [],
    "raw_output": "<return_only — not persisted>"
  },
  "provenance": {
    "shadows_received": ["<shadow_id>", "..."],
    "tiers_present": [1, 2],
    "local_tiers_present": false
  },
  "receipt_signature": {
    "key_scheme": "<scheme>",
    "node_id": "<responder>",
    "envelope_id": "<matches task envelope>",
    "inputs_received": ["<shadow_id or public block id>", "..."],
    "timestamp": "<iso8601>",
    "sig": "<signature over result>"
  }
}
```

---

### Job Envelope

A `job` is a multi-step, manifest-driven dispatch. The manifest is authored entirely
on the policy node before dispatch. The forge executes, never interprets.

A single-step `job` is semantically equivalent to a `task`. All `task` tooling
remains valid.

```json
{
  "thermocline": "0.3.0",
  "type": "job",
  "job_id": "<uuid-v4>",
  "issued_at": "<iso8601>",
  "issuer": "<node_id>",
  "channel_id": "<channel>",

  "manifest": {
    "intent": "A single natural-language sentence describing the end goal.",
    "output_contract": {
      "type": "image | audio | video | text | composite",
      "format": "png | mp4 | wav | md | ...",
      "destination": "local | return | path/on/issuer"
    },
    "constraints": {
      "may_access": ["local_models", "comfyui", "ollama"],
      "may_not_access": ["openai", "openbrain", "internet"],
      "privacy_fence": "no issuer-origin content may be logged or persisted on forge"
    },
    "result_policy": {
      "persist_to_shared": [],
      "return_only": ["artifact"],
      "strip_before_persist": ["pii", "file_references"]
    },
    "timeout_seconds": 300
  },

  "steps": [
    {
      "step_id": "s1",
      "label": "Short human-readable label",
      "tool": "<tool_id>",
      "model": "<optional — e.g. qwen2.5:7b or flux-dev>",
      "input": {
        "source": "manifest | step:<step_id>",
        "field": "intent | output | <named_field>"
      },
      "context": [
        {
          "tier": 2,
          "role": "task_background",
          "content": "<public context for this step>"
        },
        {
          "tier": 1,
          "role": "source_material",
          "shadow": {
            "shadow_id": "<opaque_id>",
            "content_type": "document",
            "abstraction": "A brand style guide from the issuer node",
            "relevance": 0.90
          }
        }
      ],
      "params": {},
      "passthrough": ["output"],
      "depends_on": []
    },
    {
      "step_id": "s2",
      "label": "Generate image from concept",
      "tool": "comfyui",
      "model": "flux-dev",
      "input": {
        "source": "step:s1",
        "field": "output"
      },
      "context": [],
      "params": {
        "width": 1024,
        "height": 1024,
        "steps": 20
      },
      "passthrough": ["output"],
      "depends_on": ["s1"]
    }
  ],

  "dispatch_signature": {
    "key_scheme": "brine",
    "node_id": "<issuer>",
    "channel_id": "<channel>",
    "policy_hash": "<hash of manifest.constraints + manifest.result_policy>",
    "shadows_generated": ["<shadow_id>", "..."],
    "timestamp": "<iso8601>",
    "sig": "<signature over canonical envelope>"
  }
}
```

### Job Result Envelope

```json
{
  "thermocline": "0.3.0",
  "type": "job_result",
  "job_id": "<matches job envelope job_id>",
  "result_id": "<uuid>",
  "status": "complete | failed | halted",
  "completed_at": "<iso8601>",
  "responder": "<node_id>",
  "halt_reason": null,
  "artifact": {
    "type": "image | audio | video | text | composite",
    "format": "png | mp4 | wav | md | ...",
    "data": "<base64 | local_path | stream_ref>"
  },
  "provenance": {
    "shadows_received": ["<shadow_id>", "..."],
    "tiers_present": [1, 2],
    "steps_executed": ["s1", "s2"],
    "local_tiers_present": false
  },
  "receipt_signature": {
    "key_scheme": "<scheme>",
    "node_id": "<responder>",
    "job_id": "<matches job envelope>",
    "inputs_received": ["<shadow_id or public block id>", "..."],
    "timestamp": "<iso8601>",
    "sig": "<signature over result>"
  }
}
```

On `failed` or `halted`, `artifact` is null and `halt_reason` carries one of the
defined halt codes. The forge flushes all execution state before returning this
envelope.

---

### Task Types

| Type | Description |
|------|-------------|
| `text.generate` | Generate text from instruction and context |
| `text.summarize` | Summarize provided content |
| `text.transform` | Rewrite, translate, or restructure content |
| `image.generate` | Generate an image from a prompt |
| `image.describe` | Describe or analyze an image |
| `code.generate` | Write code from specification |
| `code.review` | Review code for issues |
| `file.process` | Process a file (type specified in parameters) |
| `data.extract` | Extract structured data from unstructured input |
| `video.generate` | Generate video from a prompt or storyboard |
| `video.transcribe` | Transcribe spoken content from video |
| `video.describe` | Describe or analyze video content |
| `video.transform` | Edit, clip, or reformat video |
| `audio.generate` | Generate audio, music, or speech from a prompt |
| `audio.transcribe` | Transcribe spoken content from audio |
| `audio.describe` | Describe or analyze audio content |
| `audio.transform` | Edit, mix, or reformat audio |

Task types are extensible. Implementors may define custom types using reverse-domain
notation (e.g., `com.example.lim.enrich`).

---

## Identity Provider Interface

Thermocline envelopes are signed at dispatch and at receipt. The identity provider is the
system (whatever it is) that manages the keys used for signing and verification.

Any system that satisfies this interface is a valid identity provider. The spec does
not mandate a specific implementation.

### Required Capabilities

| Capability | Description |
|------------|-------------|
| `key.generate` | Generate an asymmetric keypair for a node identity |
| `key.public` | Return the public key for a given node_id |
| `key.sign(data)` | Sign arbitrary bytes with the node's private key |
| `key.verify(data, sig, node_id)` | Verify a signature against a node's public key |
| `key.rotate` | Generate a new keypair, archive the old one, publish the new public key to registered channels |
| `key.revoke` | Mark a keypair as revoked; verifiers must reject signatures from revoked keys |

### Key Schemes

The `key_scheme` field in every signature block declares the cryptographic system
in use. The identity provider implements one or more schemes.

| Scheme | Description |
|--------|-------------|
| `brine` | Locally generated keypair, managed by the identity provider (ed25519). Default. |
| `pgp` | Standard PGP key, user-managed |
| `x509` | Certificate-based, enterprise PKI |
| `none` | No signature. Valid for single-node private use only. |

*Brine is named for the hypersaline water that sinks to the deepest ocean floors and
pools there undisturbed, denser than everything above it, never mixing unless invited.
A key held locally, passed only when trust is established.
The name is the interface; ed25519 is the implementation.*

`none` is a valid declared value, honest about the absence of a trust guarantee.
It is not permitted on channels with a trust ceiling above `tier-0`.

**`none` verification contract (v0.4.0).** `none` is an explicit unsigned path,
not a bypass. A verifier presented with `key_scheme=none` MUST NOT return a
verification witness that is indistinguishable from a real one. In the reference
implementation, `verify_envelope(payload, verifier)` raises
`SchemeError(code="UNSIGNED_SCHEME_REJECTED")` for `none` unless the caller
opts in with `allow_unsigned=True`, in which case it returns a distinct
`UnsignedAck` (not a `Receipt`). A forge that requires integrity refuses `none`
by leaving `allow_unsigned` at its default. This is what lets a compute forge
(Seamount) be configured to REQUIRE a signing scheme and reject `none`.

### Platform Integration

The identity provider MUST store private keys in the platform's secure keystore:

| Platform | Recommended Store | Hardware Backing |
|----------|------------------|-----------------|
| macOS | Keychain Services | Secure Enclave on Apple Silicon |
| Linux | libsecret / Secret Service API | TPM 2.0 where available |
| Windows | Windows Credential Manager | TPM 2.0 where available |

Private keys MUST NOT be stored in plaintext files, environment variables, or
application configuration. The identity provider MUST refuse to operate if the
platform secure keystore is unavailable, rather than falling back to insecure
storage.

### Constraints

- Key scheme is declared at channel creation time and cannot change mid-session
- Scheme downgrade attempts MUST be rejected
- The public key is the node identity, so share it freely
- The private key MUST never leave the secure keystore
- Key rotation MUST be propagated to all registered channels before the old key
  is archived
- A rotated key remains valid for verification of previously signed envelopes
  but MUST NOT be used for new signatures

### Dispatch Signatures

The `dispatch_signature` block on `task` and `job` envelopes binds the envelope
to the dispatching sovereign node. It is computed over the canonical-JSON form
of the entire envelope.

**Field pre-fill ordering (SP-3.3-02, v0.3.1)**: Implementations MUST populate all non-`sig` fields of `dispatch_signature` (`key_scheme`, `node_id`, `channel_id`, `policy_hash`, `shadows_generated`, `timestamp`) BEFORE canonicalization and signing. The `sig` field SHALL be the empty string `""` during canonicalization. Failure to pre-fill any field will produce a signature that the verifier cannot reproduce. The reference implementation exposes this as `thermocline.sign_envelope(envelope, provider, signer_identity=...)`.

### Receipt Signatures

The `receipt_signature` block on `task_result` and `job_result` envelopes binds
the result to the forge that produced it. Verification reproduces the
canonicalization the signer used.

**Canonicalization invariant (SP-3.3-01, v0.3.1)**: When verifying a `receipt_signature`, implementations MUST canonicalize the envelope with the `receipt_signature.sig` field set to the empty string `""`, NOT removed. The signer SHALL produce the signature over this same canonicalization shape. Removing the field would cause map-key set divergence between signer and verifier. The reference implementation exposes verification as `thermocline.verify_envelope(payload, verifier)`.

Example (using the model-conformant `receipt_signature` field vocabulary):

```json
// Before signing / verification canonicalization:
{ "...envelope...": "...", "receipt_signature": { "key_scheme": "brine", "node_id": "...", "envelope_id": "...", "inputs_received": [], "timestamp": "...", "sig": "" } }
```

**Single signature field (SP-3.3-03, v0.4.0)**: The `sig` field is the only carrier of signature bytes, encoded as a lowercase hex string. Earlier drafts floated a `bytes_hex` tolerance alias; it is retired. Envelopes validate under `extra="forbid"`, so an unknown alias is rejected rather than silently accepted, keeping the wire single-shaped across implementations.

---

## Threat Model

Thermocline's threat model addresses attacks against the envelope layer, the contract
between nodes. Attacks against the policy engine (Photophore) and the forge (Seamount)
are covered in their respective specifications.

### Trust Assumptions

| Assumption | Implication |
|------------|------------|
| The sovereign node is honest | The entire system's trust root. If the sovereign node is compromised, all guarantees fail. This is by design. See Residual Risks. |
| The policy engine correctly classifies content | Tier assignments reflect the user's actual privacy intent. Misclassification is a policy engine bug, not an envelope bug. |
| The identity provider's secure keystore is intact | Private keys have not been exfiltrated. Platform keystore compromise is outside Thermocline's threat boundary. |
| Transport integrity exists | TLS or equivalent prevents in-transit modification. Thermocline does not re-implement transport security. |

### Attack Surfaces and Mitigations

**AT-C1: Envelope Tampering in Transit**
*Attack:* Modify envelope fields (instruction, context, result_policy) after dispatch
signature but before forge receipt.
*Mitigation:* The dispatch signature covers the canonical envelope. The forge MUST
verify the signature before processing. Any field modification invalidates the
signature → forge rejects with `SIGNATURE_INVALID`.
*Residual:* Requires transport-layer compromise (TLS break or MITM). Outside Thermocline's
threat boundary but layered defense is recommended.

**AT-C2: Envelope Replay**
*Attack:* Capture a valid signed envelope and replay it to the forge to re-execute
the same task.
*Mitigation:* `envelope_id` is a UUID. The forge MAY maintain a short-lived replay
cache (TTL = 2x configured task timeout) and reject duplicate envelope_ids.
*Residual:* Replay cache is RECOMMENDED, not REQUIRED, because statelessness is a
core forge property. A replayed task produces a duplicate result but does not leak
additional context (the envelope contains the same content as the original).

**AT-C3: Shadow Inference (Statistical Correlation)**
*Attack:* A forge or observer collects shadows across many dispatches and correlates
patterns to infer private content. Example: shadow abstraction "a financial document
from Q4" appears in every dispatch to a specific forge during January → inference
that the sovereign node is processing year-end financials.
*Mitigation:* Shadows are generated at dispatch time, not cached. The policy engine
SHOULD vary abstraction phrasing across dispatches for the same content. Shadow IDs
MUST be unique per dispatch (not stable across dispatches for the same content).
*Residual:* Statistical inference from shadow metadata is theoretically possible with
sufficient volume. This is an inherent tradeoff of the shadow primitive. Conveying
relevance without content necessarily leaks some information about the existence and
rough nature of private context. See Photophore spec for shadow quality requirements.

**AT-C4: Forged Dispatch Signature**
*Attack:* An attacker creates a Thermocline envelope with a forged dispatch signature to
impersonate a sovereign node and dispatch unauthorized work to a forge.
*Mitigation:* The forge verifies the dispatch signature against the registered public
key for the declared `node_id`. Forging requires possession of the sovereign node's
private key. Key schemes with hardware backing (Secure Enclave, TPM) make extraction
infeasible without physical access.
*Residual:* Key compromise (AT-C6) enables this attack. See key compromise below.

**AT-C5: Result Policy Escalation**
*Attack:* A forge modifies `result_policy` to persist more data than the sovereign
node authorized.
*Mitigation:* `result_policy` is part of the signed envelope. The sovereign node
authored it; the forge cannot modify it without invalidating the signature. On
result receipt, the sovereign node enforces its own result_policy. The forge's
copy is advisory; the sovereign node's copy is authoritative.
*Residual:* A compromised forge could return results that *contain* more information
than the result_policy intended (e.g., embedding private data in the output). The
sovereign node SHOULD apply strip_before_persist filters on receipt, not trust the
forge to have applied them.

**AT-C6: Key Compromise**
*Attack:* The private key of a sovereign node or forge is exfiltrated from the
platform keystore.
*Mitigation:* Hardware-backed keystores (Secure Enclave, TPM) make software-only
extraction infeasible. Key rotation limits the window of exposure. Revocation
propagates to all registered channels.
*Residual:* Physical access to the device or a platform-level exploit (OS zero-day)
can compromise any keystore. This is outside Thermocline's threat boundary. The identity
provider SHOULD support key rotation on a configurable schedule.

### Residual Risks (Accepted by Design)

**The sovereign node is the root of trust.** If it is compromised (malware,
unauthorized access, coerced operator), all privacy guarantees fail. This is not a
bug. It is the fundamental design choice of a privacy-first system. Thermocline does not
attempt to protect users from their own compromised machine because doing so would
require trusting a third party, which contradicts the design premise.

**Shadow metadata leaks existence.** The shadow primitive is designed to convey
relevance without content. By definition, this reveals that relevant private context
exists. A system that reveals nothing about private context cannot help a forge
reason about it. This is the core tradeoff.

**Replay produces duplicate work, not additional exposure.** A replayed envelope
contains the same content as the original. The worst case is wasted compute, not
privacy breach.

---

## Job Integrity Rules

The following rules apply to all `job` envelopes. A forge that cannot enforce these
rules is not a compliant job executor.

**1. Manifest Immutability**
The manifest is sealed at job open. The forge MUST NOT modify `intent`,
`output_contract`, `constraints`, or `result_policy` at any point during execution.
Any attempt to do so halts the job with `MANIFEST_TAMPER`.

**2. Passthrough Containment**
A step may only receive inputs explicitly declared in the prior step's `passthrough[]`
array. No implicit context flows between steps. Violation halts with
`PASSTHROUGH_VIOLATION`.

**3. Output Contract Validation**
After the final step completes, the forge validates the output against
`manifest.output_contract` before returning the job result envelope. Type or format
mismatch halts with `CONTRACT_MISMATCH`.

**4. Privacy Fence Enforcement**
The forge MUST NOT write step inputs or outputs to any persistent log, forward step
data to tools outside `manifest.constraints.may_access[]`, or retain any job data
after the result envelope is dispatched.

**5. Intermediate State Opacity**
The issuer receives only `job_accepted` and then `job_result`. No intermediate step
outputs are transmitted. The issuer never sees partial state.

**6. Authorship is a Policy-Node Responsibility**
The manifest is written on the issuer node before dispatch. The forge executes,
never interprets. If a step is ambiguous, the job halts with `STEP_AMBIGUOUS` and
returns to the issuer for clarification.

---

## Job Halt Codes

| Code | Meaning |
|------|---------|
| `MANIFEST_TAMPER` | Forge attempted to modify the manifest |
| `PASSTHROUGH_VIOLATION` | Step received input not declared in prior step's `passthrough[]` |
| `CONTRACT_MISMATCH` | Final output does not satisfy `output_contract` |
| `STEP_AMBIGUOUS` | A step could not be executed without interpretation |
| `TOOL_UNAVAILABLE` | A declared tool ID could not be resolved on the forge |
| `TIMEOUT` | Job exceeded `manifest.timeout_seconds` |
| `PRIVACY_VIOLATION` | Forge detected attempt to access tools outside `may_access[]` |

---

## HALT Recovery Protocol

> A halted job is a dead job.

The forge is **stateless between jobs**. On halt or failure, the forge flushes all
execution state and returns only the job result envelope (`status: halted`,
`halt_reason`, no artifact). Nothing is retained.

**Rule 1. No resume.** The issuer reissues from scratch with a new `job_id`. The
forge has no resumption mechanism and no checkpoint storage.

**Rule 2. Issuer owns retry.** If a job fails, the policy node decides whether to
reissue, modify the manifest, or abort. The forge never retries autonomously.

**Rule 3. No deduplication on the forge.** If the issuer reissues the same logical
job (e.g., after a network drop on result return), the forge executes it again.
The issuer tracks `job_id` completion locally if idempotency is required.

**Rationale:** Partial state is an attack surface. No partial state means nothing to
introspect, persist, or leak. The privacy fence is absolute because there is nothing
left to fence after execution completes.

---

## Design Constraints

These constraints are non-negotiable. Any compliant implementation must respect them.

**1. Thermocline does not enforce policy.** It provides the vocabulary. What is `local`,
`shared`, or `public` is determined entirely by the policy engine on the originating
node. Thermocline has no opinion.

**2. Shadows are one-way.** There is no mechanism in the spec to reconstruct original
content from a shadow. Shadow IDs are opaque to the receiving node.

**3. Result policy travels with the task.** The originating node declares, at dispatch
time, what the receiving node is permitted to produce. The receiving node cannot
escalate permissions.

**4. No identity in transit.** The `issuer` and `responder` fields are node identifiers,
not user identifiers. Thermocline envelopes do not carry human identity unless explicitly
placed in a `public` tier context block by the policy engine.

**5. Version is mandatory.** Every envelope must declare its Thermocline version. Parsers
must reject envelopes with unrecognized versions rather than silently degrading.

**6. The spec is transport-agnostic.** A Thermocline envelope may travel over HTTP, a local
Unix socket, a Thunderbolt network bridge, a WebSocket tunnel, or any other channel.
The spec does not care.

**7. Channel identity is mandatory for signed envelopes.** The `channel_id` field is
required whenever a `dispatch_signature` is present. An envelope without a channel
declaration cannot be verified against a trust ceiling.

**8. Key scheme is declared, not inferred.** Every signature block carries its scheme
explicitly. Verifiers must reject missing or unrecognized schemes. A channel's key
scheme is set at creation time and cannot change mid-session. Scheme downgrade
attempts must be rejected.

**9. The forge executes, never interprets.** For `job` envelopes, the forge may not
extend, rewrite, or infer beyond the manifest. Ambiguity halts; it does not prompt
autonomous resolution.

**10. Roles are composable.** Any system may implement any combination of roles
(sovereign node, policy engine, identity provider, forge, memory store). The spec
does not mandate role separation. Role composition does not alter the envelope
contract. A system acting as both sovereign node and forge still signs dispatches
and verifies receipts.

---

## What Thermocline Is Not

- It is not a memory system. Use OpenBrain, Mem0, or any other store.
- It is not a policy engine. That is Photophore, or any compliant implementation.
- It is not a compute runtime. That is Seamount, or any compliant forge.
- It is not an authentication protocol. Layer your own trust above it.
- It is not opinionated about models. Any inference backend is valid.

---

## Reference Implementations

The following reference implementations are planned or in development:

| Name | Role | Language | Status |
|------|------|----------|--------|
| Seamount | Compute forge (task + job receiver) | Swift / Python | Planned |
| Photophore | Shadow protocol (policy engine) | Python | Planned |
| thermocline-py | Python client library | Python | Planned |
| thermocline-ts | TypeScript client library | TypeScript | Planned |

---

## Versioning

Thermocline follows semantic versioning. The schema version in `"thermocline"` must be a valid
semver string. Minor versions add fields; patch versions fix ambiguities. Major versions
may break compatibility and require explicit migration.

**Forward-compatibility policy (v0.4.0).** The reference models validate with
`extra="forbid"` and accept only versions in an explicit `SUPPORTED_VERSIONS`
set, so a strict parser rejects both unknown fields and unknown versions rather
than silently degrading (Design Constraint 5). The "minor versions add fields"
rule therefore does NOT mean an older reference parser tolerates a newer minor's
new fields: a field added in a future minor is a breaking input to a strict
parser until that version is added to `SUPPORTED_VERSIONS`. Producers and
consumers advance `SUPPORTED_VERSIONS` together; a new envelope field ships in
the same release that teaches parsers to accept its declared version. Tolerant
("ignore unknown fields") parsing is intentionally not offered, because on a
privacy envelope an unrecognized field is a fail-closed condition, not a
forward-compatible one.

---

## Changelog

### 0.3.0
- Renamed schema version field from `cirdan` to `thermocline` to align with reference implementations (`pi-forge`, etc.) and the spec's own Versioning prose. Pre-release correction within the 0.3.0-draft RFC window.
- Added Role Architecture section defining five functional roles (sovereign node, policy
  engine, identity provider, forge, memory store) as composable capabilities,
  not coupled to specific systems
- Added Identity Provider Interface with required capabilities (generate, sign, verify,
  rotate, revoke), platform integration requirements (Keychain, libsecret, Credential
  Manager), and hardware backing recommendations (Secure Enclave, TPM)
- Replaced `osaurus` key scheme with generic identity provider model. Any system
  satisfying the interface is valid; no hard dependency on any specific identity system
- Added Threat Model section covering six attack surfaces (envelope tampering, replay, shadow
  inference, forged signatures, result policy escalation, key compromise) with
  mitigations and residual risk analysis
- Added Design Constraint 10 (roles are composable)
- Moved example configurations, "Relationship to Existing Systems" table, and
  "A Note on Naming" to Appendix A (non-normative)
- Updated all envelope schema versions to 0.3.0
- Added Companion Specifications header field with formal references to Photophore 0.3.0+ and Seamount 0.3.0+

### 0.2.0
- Added `job` envelope type: manifest-driven multi-step dispatch
- Added `job_result` envelope type
- Added `type` field to all envelopes (`task`, `task_result`, `job`, `job_result`)
- Added per-step `context[]` blocks with full tier/shadow support in job steps
- Added `result_policy` to job manifest (issuer-authored, forge cannot escalate)
- Added `channel_id` and `dispatch_signature` to job envelope (consistent with task)
- Added `steps_executed` to job result provenance
- Added Job Integrity Rules (rules 1–6)
- Added Job Halt Codes table
- Added HALT Recovery Protocol
- Added Design Constraint 9 (forge executes, never interprets)
- Updated Seamount reference to cover task + job reception

### 0.1.0
- Initial draft release
- Task envelope and task result envelope
- Privacy tier system (0/1/2)
- Shadow block definition
- Result policy
- Dispatch and receipt signatures (key scheme: brine)
- Task types: text, image, code, file, data, video, audio
- Design constraints 1–8
- Reference implementations registry

---

## Architecture Decision Records

Forever-decisions of the `thermocline-py` reference implementation are recorded
as ADRs under [docs/adr/](docs/adr/index.md). See:

- [ADR-0001: Python 3.11 as primary language](docs/adr/ADR-0001-python-3-11-as-primary-language.md)
- [ADR-0002: Pydantic v2 lock-in](docs/adr/ADR-0002-pydantic-v2-lock-in.md)
- [ADR-0003: Single canonical JSON path](docs/adr/ADR-0003-single-canonical-json-path.md)
- [ADR-0004: BLAKE3 with `algo_version` chain](docs/adr/ADR-0004-blake3-with-algo-version.md)
- [ADR-0005: No in-process key material](docs/adr/ADR-0005-no-in-process-key-material.md)

Photophore and Seamount cross-reference these ADRs from their own READMEs.

---

## Appendix A (Non-Normative)

### Example Configurations

Thermocline is transport-agnostic and hardware-agnostic. The same envelope format works
across all of these configurations.

**Laptop → Desktop (local, high-bandwidth)**
A personal laptop acts as the sovereign node (private files, personal context,
policy engine running locally). A desktop or more powerful machine on the same network
or connected directly (e.g., via Thunderbolt) acts as the forge. Tasks dispatch
over the local link; results write back to the laptop. No cloud involved.

**Workstation → Remote GPU (network, cloud forge)**
A developer's workstation dispatches image generation or model inference tasks to
a rented GPU instance. The envelope travels over HTTPS. The forge never receives
the private prompt or source material, only the shadow and the task parameters.

**Personal node → Team node (memory sync)**
A personal memory instance and a shared team instance maintain a channel. Only
tier-2 memories flow to the team node. Personal context, private conversations,
and sensitive files never leave the personal instance. The team sees only what the
owner has explicitly cleared as public.

**Mobile → Desktop (sovereign mobile node)**
A phone or tablet acts as the personal sovereign node, always with the user,
holding private context. A desktop handles heavy processing as a forge. The mobile
device dispatches tasks and receives results; the desktop never holds state between
sessions.

**Local terminal → Hosted agent**
A command-line workflow dispatches tasks to a hosted agent. The terminal is the
policy node; the agent system is the forge. The agent receives only what the Thermocline
envelope contains: the task, public context, and shadows. It never receives the
private context that motivated the work. The envelope is the only thing that
crosses the network.

### Relationship to Existing Systems

| System | Relationship |
|--------|-------------|
| OpenBrain | Thermocline results may commit to OpenBrain via the policy engine's persist policy |
| OpenClaw | OpenClaw can play any role in the suite (sovereign node, policy engine, identity provider, forge, or all simultaneously). As a forge, it operates on what the envelope contains and never receives tier-0 content. |
| Osaurus | Osaurus agents on a sovereign node may provide cryptographic node identity via the identity provider interface. Not required. Any system satisfying the interface is valid. |
| OpenViking | Thermocline is transport; OpenViking could serve as a context store behind it |
| Vertex Memory Bank | Thermocline is transport; Memory Bank could be a `public`-tier persist target |
| MCP | Thermocline envelopes could be wrapped in MCP tool calls (not required) |

### A Note on Naming

A thermocline is a sharp, invisible boundary between two layers of ocean water
(warm surface water above, cold deep water below). The two worlds coexist without
touching. Things cross the boundary, but they arrive changed by the crossing: warmer
things cool, denser things rise. The thermocline is not a wall. It is an interface.
Work passes through it; private context does not.

This spec is named for that boundary. It defines the interface between what a node
holds and what it dispatches, between what is private and what may cross. It holds
nothing itself. It enables the crossing.

The names in this suite form a coherent system: Thermocline defines the boundary.
Photophore generates the shadow. Seamount forges the work. Each name describes the
physics of what it does before a line of code is read.

If you build something in this ecosystem, name it well.

---

*Thermocline is maintained as an open community specification. MIT licensed.*
*Companion projects: Seamount (compute forge) · Photophore (shadow protocol)*
