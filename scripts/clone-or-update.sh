#!/usr/bin/env bash

set -euo pipefail

# Modes:
#   pinned   - the checkout mirrors upstream and nothing local is worth keeping,
#              so it is reset to origin/HEAD. Refuses when the checkout holds
#              commits origin/HEAD does not, because the reset would drop them.
#   writable - the checkout is edited in place (~/.claude symlinks into
#              claude-code-prompts, and Claude Code rewrites settings.json), so
#              it only fast-forwards and never touches the working tree.

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <base-directory> <repository-url> <pinned|writable>" >&2
    exit 1
fi

BASE_DIR="$1"
REPO_URL="$2"
MODE="$3"

case "$MODE" in
    pinned | writable) ;;
    *)
        echo "Unknown mode '$MODE'; expected 'pinned' or 'writable'." >&2
        exit 1
        ;;
esac

# Extract org/repo from URL (handles https://host/org/repo and git@host:org/repo)
ORG_REPO=$(echo "$REPO_URL" | sed -E -e 's|^https?://[^/]+/||' -e 's|^[^:]+:||' -e 's|\.git$||')
TARGET_DIR="$BASE_DIR/$ORG_REPO"

if [ ! -d "$TARGET_DIR/.git" ]; then
    mkdir -p "$(dirname "$TARGET_DIR")"
    git clone "$REPO_URL" "$TARGET_DIR"
    exit 0
fi

git -C "$TARGET_DIR" fetch origin

if [ "$MODE" = "writable" ]; then
    if ! git -C "$TARGET_DIR" merge --ff-only origin/HEAD; then
        echo "$TARGET_DIR has diverged from origin/HEAD; push or rebase it, then rerun." >&2
        exit 1
    fi
    exit 0
fi

unpushed=$(git -C "$TARGET_DIR" rev-list --count origin/HEAD..HEAD)
if [ "$unpushed" -ne 0 ]; then
    echo "$TARGET_DIR holds $unpushed commit(s) that origin/HEAD does not." >&2
    echo "Resetting would destroy them. Push them, drop them, or switch this clone to writable mode." >&2
    exit 1
fi

git -C "$TARGET_DIR" reset --hard origin/HEAD
