#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <base-directory> <repository-url>" >&2
    exit 1
fi

BASE_DIR="$1"
REPO_URL="$2"

ORG_REPO=$(echo "$REPO_URL" | sed -e 's|.*github\.com[:/]||' -e 's|\.git$||')
TARGET_DIR="$BASE_DIR/$ORG_REPO"

if [ -d "$TARGET_DIR/.git" ]; then
    echo "Running: git -C \"$TARGET_DIR\" pull --ff-only"
    git -C "$TARGET_DIR" pull --ff-only
else
    echo "Running: git clone \"$REPO_URL\" \"$TARGET_DIR\""
    mkdir -p "$(dirname "$TARGET_DIR")"
    git clone "$REPO_URL" "$TARGET_DIR"
fi
