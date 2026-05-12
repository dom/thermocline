# Thermocline Suite Quickstart

A 30-minute walkthrough: clone three repos → install → first dispatch → audit
query → audit export. Target: under 30 minutes on a clean macOS 12+ box with
Python 3.11 already installed.

## 1. Prerequisites

- macOS 12+ (Apple Silicon or Intel). Linux works but is not first-class.
- Python 3.11+ on `$PATH`.
- ~500 MB of disk for the three repos + Python deps.
- A terminal with `git`, `curl`, and `bash` (default macOS shells are fine).

Optional but recommended: [`uv`](https://docs.astral.sh/uv/) for fast venv
management. The walkthrough shows both `uv` and plain `pip` paths.

## 2. Clone (sibling layout)

The reference dev layout puts the three repos as siblings under
`~/Projects/dom/`. The ADR cross-references and the release script assume this
shape; deviating will require setting `THERMOCLINE_SUITE_ROOT`.

```bash
mkdir -p ~/Projects/dom
cd ~/Projects/dom
git clone https://github.com/graywhale/thermocline.git
git clone https://github.com/graywhale/photophore.git
git clone https://github.com/graywhale/seamount.git
```

## 3. Install all five Python packages

Recommended (`uv`):

```bash
cd ~/Projects/dom/thermocline/thermocline/python && uv venv && uv pip install -e .[dev]
cd ~/Projects/dom/photophore/python                && uv venv && uv pip install -e .[dev]
cd ~/Projects/dom/seamount/pi-forge                && uv venv && uv pip install -e .[dev]
cd ~/Projects/dom/seamount/describe-forge          && uv venv && uv pip install -e .[dev]
cd ~/Projects/dom/seamount/conformance             && uv venv && uv pip install -e .[dev]
```

Plain pip:

```bash
cd ~/Projects/dom/thermocline/thermocline/python && python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]
# ...repeat for each of the other 4 packages
```

**Time budget:** ~12 minutes for cold pip dependency resolution on a fresh box.

## 4. First-time keystore setup

Each forge maintains its own signing identity under its own `python-keyring`
service namespace. Initialize:

```bash
python -m pi_forge init --keyring-service seamount.piforge
python -m describe_forge init --keyring-service seamount.describeforge
```

The sovereign node's signing identity (used by `photophore channel new`) is
created lazily on first channel creation — no explicit init step.

### macOS first-prompt gotchas

- First `pi-forge init` triggers Keychain prompt **"pi-forge wants to access seamount.piforge"**.
  Click **"Always Allow"** to avoid re-prompting on every dispatch.
- Same pattern for `describe-forge init` (service `seamount.describeforge`).
- Subsequent `photophore channel new` triggers a third Keychain prompt for the
  `thermocline.brine` service (the sovereign node's keypair).
- The Python process must be signed for the "Always Allow" choice to persist.
  Homebrew Python and `pyenv`-installed Python are signed correctly. If you
  see re-prompts on every dispatch, check `codesign -dv $(which python3)`.

**Time budget:** ~1 minute per forge once you know which dialog to click.

## 5. Start a forge

In a separate terminal, run:

```bash
python -m pi_forge serve --keyring-service seamount.piforge --port 5117
```

Wait for the readiness marker:

```
PIFORGE_READY port=5117
```

The marker is contractual — the Photophore integration-test harness greps for
this exact line. Keep the forge process running for the remaining steps.

## 6. Create a channel (TOFU pubkey fetch)

In your original terminal:

```bash
photophore channel new \
  --remote-node pi-forge-local \
  --ceiling tier-2 \
  --key-scheme brine \
  --fetch-pubkey-from http://localhost:5117
```

Expected output: a fresh channel UUID. The `--fetch-pubkey-from` flag is
**Trust On First Use** — Photophore fetches the forge's published public key
from `GET /pubkey`, stores it in the trust store, and any subsequent forge
signature must verify against it. Tamper-evident.

Capture the channel UUID for the next step (or use `photophore channel list`).

## 7. Dispatch a task

```bash
photophore dispatch \
  --channel <CHANNEL_UUID> \
  --task examples/task-pi-100-digits.json \
  --forge-url http://localhost:5117
```

Expected output: a `task_result` JSON envelope with the first 100 digits of π
and a `receipt_signature` block. The dispatch coordinator runs all 9 steps
(canonicalize → classify → shadow → policy → sign → POST → verify → record →
audit-write) and exits 0 on success.

## 8. Inspect the audit log

Query entries for this channel:

```bash
photophore audit query --channel <CHANNEL_UUID>
```

Expected: a list of audit entries including `channel_new`, `dispatch_pre`,
`dispatch_post`, and (per CLI-06) `cli.invoked` entries for every CLI
invocation you've run.

Export the full audit log as JSONL:

```bash
photophore audit export > audit.jsonl
```

Verify the chain integrity:

```bash
photophore audit verify
```

Expected: `ok: audit chain verified (N entries, chain head <blake3 hex>)`.

## 9. Cleanup (optional)

```bash
photophore channel close <CHANNEL_UUID> --reason "quickstart complete"
```

The audit log preserves the close entry forever (append-only). You can re-open
a new channel with `photophore channel new` whenever you want.

## 10. Next steps

- [Thermocline-py install](install.md) and [ops](ops.md).
- [Photophore install](../../photophore/docs/install.md) and [ops](../../photophore/docs/ops.md).
- Seamount install: [pi-forge](../../seamount/pi-forge/docs/install.md),
  [describe-forge](../../seamount/describe-forge/docs/install.md),
  [conformance](../../seamount/conformance/docs/install.md).
- [Architecture Decision Records (Thermocline)](adr/index.md).

**Total wall-clock time:** ~17 minutes core flow + ~5 minutes Keychain dialog
buffer = under 30 minutes on a clean box. Slower disks or first-time
dep-resolution may push install to 15+ minutes.
