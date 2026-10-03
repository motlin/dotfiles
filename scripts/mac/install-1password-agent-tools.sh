#!/usr/bin/env bash

set -euo pipefail

# Mac only.

if ! claude plugin marketplace list --json | jq --exit-status 'any(.[]; .name == "1password")' >/dev/null; then
    claude plugin marketplace add 1Password/1password-claude-plugin
fi

if ! claude plugin list --json | jq --exit-status 'any(.[]; .id == "1password@1password")' >/dev/null; then
    claude plugin install 1password@1password
fi

# Codex has no plugin for it.
if ! codex mcp get 1password >/dev/null 2>&1; then
    codex mcp add 1password -- 1password-mcp
fi
