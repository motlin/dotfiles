#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <base-directory> <repository-url>" >&2
    exit 1
fi

BASE_DIR="$1"
REPO_URL="$2"

# Extract org/repo from URL (handles https://host/org/repo and git@host:org/repo)
ORG_REPO=$(echo "$REPO_URL" | sed -E -e 's|^https?://[^/]+/||' -e 's|^[^:]+:||' -e 's|\.git$||')
TARGET_DIR="$BASE_DIR/$ORG_REPO"

if [ -d "$TARGET_DIR/.git" ]; then
    git -C "$TARGET_DIR" fetch origin
    git -C "$TARGET_DIR" reset --hard origin/HEAD
else
    mkdir -p "$(dirname "$TARGET_DIR")"
    git clone "$REPO_URL" "$TARGET_DIR"
fi
