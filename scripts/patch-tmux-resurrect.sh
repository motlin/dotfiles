#!/usr/bin/env bash

set -euo pipefail

# Apply PR #541 to tmux-resurrect: "Update symlink only after the content archive is ready"
# https://github.com/tmux-plugins/tmux-resurrect/pull/541
#
# This fixes a race condition where the `last` symlink can point to a
# nonexistent file if the system shuts down mid-save.
#
# Idempotent: safe to run multiple times. Re-applies after tpm updates.

RESURRECT_DIR="${HOME}/.config/tmux/plugins/tmux-resurrect"

if [ ! -d "$RESURRECT_DIR/.git" ]; then
    echo "tmux-resurrect not installed yet at $RESURRECT_DIR, skipping patch"
    exit 0
fi

cd "$RESURRECT_DIR"

PR_BRANCH="pr-541"
PR_REF="pull/541/head"

# Fetch the PR
if ! git fetch origin "$PR_REF:$PR_BRANCH" --force 2>/dev/null; then
    echo "Warning: could not fetch PR #541 (network issue?), skipping patch"
    exit 0
fi

# Check how many commits the PR has ahead of master
PR_COMMITS=$(git log --oneline "master..$PR_BRANCH" 2>/dev/null)
if [ -z "$PR_COMMITS" ]; then
    echo "PR #541 has no commits ahead of master (already merged?), skipping"
    git branch -D "$PR_BRANCH" 2>/dev/null || true
    exit 0
fi

# Check if the PR commits are already applied (cherry-pick detection)
ALL_APPLIED=true
while IFS= read -r line; do
    commit_hash=$(echo "$line" | awk '{print $1}')
    commit_msg=$(echo "$line" | cut -d' ' -f2-)
    # Check if a commit with the same message exists on current HEAD
    if ! git log --oneline HEAD | grep -qF "$commit_msg"; then
        ALL_APPLIED=false
        break
    fi
done <<< "$PR_COMMITS"

if [ "$ALL_APPLIED" = true ]; then
    echo "PR #541 already applied to tmux-resurrect, skipping"
    git branch -D "$PR_BRANCH" 2>/dev/null || true
    exit 0
fi

# Reset to origin/master first (in case a stale cherry-pick is present)
git checkout master 2>/dev/null
git reset --hard origin/master 2>/dev/null

# Cherry-pick all PR commits
echo "Applying PR #541 to tmux-resurrect..."
if git cherry-pick "$PR_BRANCH" --no-edit 2>/dev/null; then
    echo "PR #541 applied successfully"
else
    echo "Warning: cherry-pick failed (conflict?), aborting"
    git cherry-pick --abort 2>/dev/null || true
fi

git branch -D "$PR_BRANCH" 2>/dev/null || true
