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

# mise shims a command when any installed Node version provides it, not just the active one.
function remove_npm_global_from_mise_nodes() {
    local package="$1"
    local node_version

    command -v mise >/dev/null 2>&1 || return 0
    for node_version in $(mise ls --installed node | awk '{ print $2 }'); do
        if mise exec "node@${node_version}" -- npm ls --global --depth=0 "${package}" >/dev/null 2>&1; then
            mise exec "node@${node_version}" -- npm uninstall --global "${package}"
        fi
    done
}

function remove_npm_global() {
    local package="$1"

    remove_npm_global_from_mise_nodes "${package}"

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

# Drop shims for the copies removed above, or the Codex installer still sees them on PATH and edits ~/.zprofile.
function reshim_mise() {
    command -v mise >/dev/null 2>&1 || return 0
    mise reshim
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

function verify_native_first_on_path() {
    local command_name="$1"
    local resolved

    resolved="$(command -v "${command_name}" || true)"
    if [[ "${resolved}" != "${NATIVE_BIN_DIR}/${command_name}" ]]; then
        echo "${command_name} resolves to ${resolved} instead of ${NATIVE_BIN_DIR}/${command_name}; remove that copy and run ./install again." >&2
        exit 1
    fi
}

remove_mise_tool "npm:@openai/codex"
remove_npm_global "@openai/codex"
remove_brew_cask "codex"
reshim_mise
install_native codex "https://chatgpt.com/codex/install.sh" sh

remove_mise_tool "npm:@anthropic-ai/claude-code"
remove_npm_global "@anthropic-ai/claude-code"
remove_brew_cask "claude-code"
reshim_mise
install_native claude "https://claude.ai/install.sh" bash

verify_native_first_on_path codex
verify_native_first_on_path claude
