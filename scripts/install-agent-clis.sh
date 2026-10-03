#!/usr/bin/env bash

set -euo pipefail

# Claude Code and Codex come only from their native installers, which update themselves.
# Copies installed through mise, npm, or Homebrew are removed so PATH order cannot pick a stale one.

readonly NATIVE_BIN_DIR="${HOME}/.local/bin"

function remove_mise_tool() {
    local tool="$1"

    command -v mise >/dev/null 2>&1 || return 0
    if [[ -n "$(mise ls --installed "${tool}")" ]]; then
        mise uninstall --all "${tool}"
    fi
}

function remove_npm_global() {
    local package="$1"

    command -v npm >/dev/null 2>&1 || return 0
    if npm ls --global --depth=0 "${package}" >/dev/null 2>&1; then
        npm uninstall --global "${package}"
    fi
}

function remove_brew_cask() {
    local cask="$1"

    command -v brew >/dev/null 2>&1 || return 0
    if brew list --cask "${cask}" >/dev/null 2>&1; then
        brew uninstall --cask "${cask}"
    fi
}

function install_native() {
    local command_name="$1"
    local installer_url="$2"
    local interpreter="$3"

    [[ -x "${NATIVE_BIN_DIR}/${command_name}" ]] && return 0

    # With the install directory already on PATH, the Codex installer leaves ~/.zprofile alone.
    curl -fsSL "${installer_url}" |
        PATH="${NATIVE_BIN_DIR}:${PATH}" CODEX_NON_INTERACTIVE=true "${interpreter}"
}

remove_mise_tool "npm:@openai/codex"
remove_npm_global "@openai/codex"
remove_brew_cask "codex"
install_native codex "https://chatgpt.com/codex/install.sh" sh

remove_mise_tool "npm:@anthropic-ai/claude-code"
remove_npm_global "@anthropic-ai/claude-code"
remove_brew_cask "claude-code"
install_native claude "https://claude.ai/install.sh" bash
