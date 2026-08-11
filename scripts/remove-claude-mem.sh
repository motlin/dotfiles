#!/usr/bin/env bash

set -euo pipefail

for required_command in claude jq trash; do
    if ! command -v "${required_command}" >/dev/null 2>&1; then
        echo "${required_command} is required to remove claude-mem." >&2
        exit 1
    fi
done

readonly CLAUDE_MEM_PLUGIN="claude-mem@thedotmack"
readonly CLAUDE_MEM_MARKETPLACE="thedotmack"

function rewrite_json() {
    local filter="$1"
    local json_file="$2"
    local temporary_file

    if [[ ! -f "${json_file}" ]]; then
        return
    fi

    temporary_file="$(mktemp "${json_file}.claude-mem-cleanup.XXXXXX")"
    cp -p "${json_file}" "${temporary_file}"
    jq "${filter}" "${json_file}" >"${temporary_file}"

    if cmp -s "${json_file}" "${temporary_file}"; then
        rm -f -- "${temporary_file}"
    else
        mv "${temporary_file}" "${json_file}"
    fi
}

function trash_path() {
    local path="$1"

    if [[ -e "${path}" || -L "${path}" ]]; then
        trash "${path}"
    fi
}

function stop_claude_mem_processes() {
    local attempt
    local process_id
    local process_ids=()

    while IFS= read -r process_id; do
        process_ids+=("${process_id}")
    done < <(
        ps -axo pid=,command= |
            awk '
                /\/\.claude\/plugins\/cache\/thedotmack\/claude-mem\// ||
                /--data-dir .*\/\.claude-mem\// {
                    print $1
                }
            '
    )

    if ((${#process_ids[@]} == 0)); then
        return
    fi

    kill -TERM "${process_ids[@]}" 2>/dev/null || true

    for ((attempt = 0; attempt < 50; attempt++)); do
        for process_id in "${process_ids[@]}"; do
            if kill -0 "${process_id}" 2>/dev/null; then
                sleep 0.1
                continue 2
            fi
        done
        return
    done

    for process_id in "${process_ids[@]}"; do
        if kill -0 "${process_id}" 2>/dev/null; then
            kill -KILL "${process_id}"
        fi
    done
}

function remove_claude_mem_plugin() {
    local installed_plugins
    local marketplaces

    installed_plugins="$(claude plugin list --json)"
    if jq --exit-status \
        --arg plugin_identifier "${CLAUDE_MEM_PLUGIN}" \
        'any(.[]; .id == $plugin_identifier and .scope == "user")' \
        <<<"${installed_plugins}" >/dev/null; then
        claude plugin uninstall \
            --prune \
            --yes \
            --scope user \
            "${CLAUDE_MEM_PLUGIN}"
    fi

    marketplaces="$(claude plugin marketplace list --json)"
    if jq --exit-status \
        --arg marketplace_name "${CLAUDE_MEM_MARKETPLACE}" \
        'any(.[]; .name == $marketplace_name)' \
        <<<"${marketplaces}" >/dev/null; then
        claude plugin marketplace remove "${CLAUDE_MEM_MARKETPLACE}"
    fi
}

function remove_claude_mem_directories() {
    local claude_mem_path
    local claude_mem_paths=(
        "${HOME}/.claude-mem"
        "${HOME}/.claude/plugins/cache/thedotmack"
        "${HOME}/.claude/plugins/data/claude-mem-thedotmack"
        "${HOME}/.claude/plugins/marketplaces/thedotmack"
    )
    local npx_cache_entry
    local package_directory

    for claude_mem_path in "${claude_mem_paths[@]}"; do
        trash_path "${claude_mem_path}"
    done

    if [[ -d "${HOME}/.claude/projects" ]]; then
        while IFS= read -r -d '' claude_mem_path; do
            trash_path "${claude_mem_path}"
        done < <(
            find "${HOME}/.claude/projects" \
                -maxdepth 1 \
                -type d \
                -name '*-claude-mem-observer-sessions' \
                -print0
        )
    fi

    if [[ -d "${HOME}/Library/Caches/claude-cli-nodejs" ]]; then
        while IFS= read -r -d '' claude_mem_path; do
            trash_path "${claude_mem_path}"
        done < <(
            find "${HOME}/Library/Caches/claude-cli-nodejs" \
                -type d \
                -name 'mcp-logs-plugin-claude-mem-mcp-search' \
                -print0
        )
    fi

    if [[ -d "${HOME}/.npm/_npx" ]]; then
        while IFS= read -r -d '' package_directory; do
            npx_cache_entry="$(dirname "$(dirname "${package_directory}")")"
            trash_path "${npx_cache_entry}"
        done < <(
            find "${HOME}/.npm/_npx" \
                -mindepth 3 \
                -maxdepth 3 \
                -type d \
                -path '*/node_modules/claude-mem' \
                -print0
        )
    fi
}

function remove_claude_mem_metadata() {
    # A leftover enabledPlugins key makes Claude reinstall the plugin on startup.
    rewrite_json \
        'if (.enabledPlugins? | type) == "object"
        then del(.enabledPlugins["'"${CLAUDE_MEM_PLUGIN}"'"])
        else . end' \
        "${HOME}/.claude/settings.json"

    rewrite_json \
        'if (.permissions.allow? | type) == "array" then
            .permissions.allow |= map(
                select(
                    type != "string"
                    or (startswith("mcp__plugin_claude-mem_") | not)
                )
            )
        else . end' \
        "${HOME}/.claude/settings.json"

    rewrite_json \
        'if (.skillUsage? | type) == "object" then
            .skillUsage |= with_entries(
                select(.key | startswith("claude-mem:") | not)
            )
        else . end' \
        "${HOME}/.claude.json"
}

function remove_claude_mem_from_tmux_snapshots() {
    local snapshot
    local temporary_file
    local tmux_resurrect_directory="${HOME}/.local/share/tmux/resurrect"

    if [[ ! -d "${tmux_resurrect_directory}" ]]; then
        return
    fi

    while IFS= read -r -d '' snapshot; do
        temporary_file="$(mktemp "${snapshot}.claude-mem-cleanup.XXXXXX")"
        cp -p "${snapshot}" "${temporary_file}"
        awk 'tolower($0) !~ /claude[-_]?mem|thedotmack/' \
            "${snapshot}" >"${temporary_file}"

        if cmp -s "${snapshot}" "${temporary_file}"; then
            rm -f -- "${temporary_file}"
        else
            mv "${temporary_file}" "${snapshot}"
        fi
    done < <(
        find "${tmux_resurrect_directory}" \
            -maxdepth 1 \
            -type f \
            -name 'tmux_resurrect_*.txt' \
            -print0
    )
}

stop_claude_mem_processes
remove_claude_mem_plugin
remove_claude_mem_directories
remove_claude_mem_metadata
remove_claude_mem_from_tmux_snapshots
