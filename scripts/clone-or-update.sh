#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <repository-url> <target-directory>" >&2
    exit 1
fi

REPO_URL="$1"
TARGET_DIR="$2"

if [ -d "$TARGET_DIR/.git" ]; then
    echo "🔄 Updating $(basename "$TARGET_DIR")"
    git -C "$TARGET_DIR" pull --ff-only
else
    echo "📥 Cloning $(basename "$TARGET_DIR")"
    git clone "$REPO_URL" "$TARGET_DIR"
fi
