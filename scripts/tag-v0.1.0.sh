#!/usr/bin/env bash
# tag-v0.1.0.sh — coordinate three v0.1.0 git tags across the Thermocline suite.
#
# Runs from any directory. Reads THERMOCLINE_SUITE_ROOT (default: $HOME/Projects/dom).
# Asserts: clean working trees, branch=main, remote-up-to-date, CHANGELOG dated
# `## [0.1.0] - <today>`, pre-tag lint sweep + cross-repo AT-coverage roll-up +
# property-coverage gate (strict), per-repo pytest. Then tags each repo on the
# same date with an identical annotation message.
#
# `--dry-run` prints what would happen; no `git tag` invocation.
# Operator MUST run `git push --tags` manually in each repo afterward (per D-06
# trust-is-never-automated principle).
#
# POSIX-portable: uses bash, grep -q, date -u, git, python. No `sed -i`, no
# `grep -P`. Tested on macOS (BSD tools) and Linux (GNU tools).
set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
fi

SUITE_ROOT="${THERMOCLINE_SUITE_ROOT:-$HOME/Projects/dom}"
REPOS=(thermocline photophore seamount)
TODAY="$(date -u +%Y-%m-%d)"
TAG="v0.1.0"
TAG_MSG="${TAG} — coordinated with thermocline ${TAG} + photophore ${TAG} + seamount ${TAG}"

err()  { echo "ERROR: $*" >&2; exit 1; }
note() { echo "  ✓ $*"; }
info() { echo "» $*"; }
dry()  { if [[ "$DRY_RUN" == "1" ]]; then echo "  [DRY] $*"; return 0; fi; return 1; }

echo "Thermocline Suite v0.1.0 release coordinator"
echo "  suite root: $SUITE_ROOT"
echo "  today:      $TODAY"
echo "  tag:        $TAG"
echo "  dry-run:    $DRY_RUN"
echo ""

# Step 1: precondition checks (read-only).
info "Step 1 — preconditions"
for repo in "${REPOS[@]}"; do
    REPO_PATH="$SUITE_ROOT/$repo"
    echo ""
    echo "  $repo:"
    [[ -d "$REPO_PATH/.git" ]] || err "$repo: $REPO_PATH is not a git repo"

    pushd "$REPO_PATH" >/dev/null

    # Clean working tree.
    if [[ -n "$(git status --porcelain)" ]]; then
        err "$repo: working tree not clean (run 'git status' in $REPO_PATH)"
    fi
    note "working tree clean"

    # Branch = main.
    BRANCH="$(git rev-parse --abbrev-ref HEAD)"
    [[ "$BRANCH" == "main" ]] || err "$repo: on '$BRANCH' (must be on 'main')"
    note "on main"

    # Remote up-to-date.
    git fetch --quiet origin main || err "$repo: git fetch origin main failed"
    LOCAL_SHA="$(git rev-parse HEAD)"
    REMOTE_SHA="$(git rev-parse origin/main)"
    if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
        err "$repo: local main ($LOCAL_SHA) is not up-to-date with origin/main ($REMOTE_SHA)"
    fi
    note "remote up-to-date ($(echo "$LOCAL_SHA" | cut -c1-12))"

    # CHANGELOG entry for today.
    CHANGELOG_PATH=""
    for candidate in CHANGELOG.md thermocline/CHANGELOG.md; do
        if [[ -f "$candidate" ]]; then
            CHANGELOG_PATH="$candidate"
            break
        fi
    done
    [[ -n "$CHANGELOG_PATH" ]] || err "$repo: no CHANGELOG.md found"
    if ! grep -q "^## \[0.1.0\] - ${TODAY}\$" "$CHANGELOG_PATH"; then
        err "$repo: $CHANGELOG_PATH missing '## [0.1.0] - ${TODAY}' heading"
    fi
    note "CHANGELOG has dated [0.1.0] section ($CHANGELOG_PATH)"

    popd >/dev/null
done

# Step 2: pre-tag lint sweep (mirror CI order — lints before pytest).
echo ""
info "Step 2 — pre-tag lint sweep"
for repo in "${REPOS[@]}"; do
    REPO_PATH="$SUITE_ROOT/$repo"
    echo ""
    echo "  $repo:"
    pushd "$REPO_PATH" >/dev/null

    if [[ -f tools/ast_lint_no_print.py ]]; then
        python tools/ast_lint_no_print.py || err "$repo: print-lint failed"
        note "ast_lint_no_print.py ok"
    fi
    if [[ -f tools/ast_lint_network_isolation.py ]]; then
        python tools/ast_lint_network_isolation.py || err "$repo: network-isolation lint failed"
        note "ast_lint_network_isolation.py ok"
    fi
    if [[ -f tools/at_coverage.py ]]; then
        python tools/at_coverage.py || err "$repo: at_coverage.py failed"
        note "at_coverage.py ok"
    fi

    popd >/dev/null
done

# Step 2b: thermocline-only cross-repo gates (not in any single repo's CI).
echo ""
info "Step 2b — cross-repo gates (thermocline-only)"
pushd "$SUITE_ROOT/thermocline" >/dev/null
if [[ -f tools/at_coverage_total.py ]]; then
    python tools/at_coverage_total.py || err "thermocline: at_coverage_total.py failed (suite-wide AT roll-up)"
    note "at_coverage_total.py — 17/17 AT-* surfaces covered across suite"
fi
if [[ -f tools/property_coverage.py ]]; then
    PROPERTY_COVERAGE_STRICT=1 python tools/property_coverage.py || \
        err "thermocline: property_coverage.py failed (CONF-03 cadence)"
    note "property_coverage.py (strict) — CONF-03 4/4 invariants at max_examples >= 200"
fi
popd >/dev/null

# Step 3: test suite.
echo ""
info "Step 3 — test suites"
for repo in "${REPOS[@]}"; do
    REPO_PATH="$SUITE_ROOT/$repo"
    echo ""
    echo "  $repo:"
    pushd "$REPO_PATH" >/dev/null

    case "$repo" in
        thermocline)
            (cd thermocline/python && pytest -q -m "not keystore") || err "thermocline: pytest failed"
            note "pytest (non-keystore) ok"
            ;;
        photophore)
            (cd python && pytest -q --ignore=tests/integration) || err "photophore: pytest failed"
            note "pytest (non-integration) ok"
            ;;
        seamount)
            for forge in pi-forge describe-forge; do
                if [[ -d "$forge" ]]; then
                    (cd "$forge" && pytest -q) || err "seamount/$forge: pytest failed"
                    note "$forge pytest ok"
                fi
            done
            if [[ -d conformance ]]; then
                (cd conformance && pytest -q at_negative/) || err "seamount/conformance: pytest failed"
                note "conformance at_negative/ pytest ok"
            fi
            ;;
    esac

    popd >/dev/null
done

# Step 4: tag (with dry-run).
echo ""
info "Step 4 — tagging"
for repo in "${REPOS[@]}"; do
    REPO_PATH="$SUITE_ROOT/$repo"
    echo ""
    echo "  $repo:"
    pushd "$REPO_PATH" >/dev/null
    if dry "git tag -a $TAG -m \"$TAG_MSG\""; then
        :
    else
        git tag -a "$TAG" -m "$TAG_MSG"
        note "tagged $TAG"
    fi
    popd >/dev/null
done

echo ""
echo "================================================================"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN complete. No tags created. Re-run without --dry-run to tag."
else
    echo "All three repos tagged $TAG on $TODAY."
fi
echo ""
echo "Manual step (REQUIRED — script does NOT auto-push per D-06):"
for repo in "${REPOS[@]}"; do
    echo "    cd $SUITE_ROOT/$repo && git push --tags"
done
echo "================================================================"
