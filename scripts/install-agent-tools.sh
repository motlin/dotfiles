#!/usr/bin/env bash

set -euo pipefail

for required_command in claude codex jq npx; do
    if ! command -v "${required_command}" >/dev/null 2>&1; then
        echo "${required_command} is required to install agent plugins and skills." >&2
        exit 1
    fi
done

function ensure_claude_marketplace() {
    local marketplace_name="$1"
    local marketplace_source="$2"
    local marketplaces
    local source_type
    local source_repository

    marketplaces="$(claude plugin marketplace list --json)"
    source_type="$(
        jq --raw-output \
            --arg marketplace_name "${marketplace_name}" \
            '.[] | select(.name == $marketplace_name) | .source' \
            <<<"${marketplaces}"
    )"

    if [[ -z "${source_type}" ]]; then
        claude plugin marketplace add "${marketplace_source}"
        return
    fi

    if [[ "${source_type}" == "github" ]]; then
        source_repository="$(
            jq --raw-output \
                --arg marketplace_name "${marketplace_name}" \
                '.[] | select(.name == $marketplace_name) | .repo' \
                <<<"${marketplaces}"
        )"
        if [[ "${source_repository}" != "${marketplace_source}" ]]; then
            echo "${marketplace_name} points to unexpected repository ${source_repository}." >&2
            exit 1
        fi
        claude plugin marketplace update "${marketplace_name}"
        return
    fi

    echo "Using existing Claude ${marketplace_name} ${source_type} marketplace."
}

function claude_marketplace_manifest() {
    local marketplace_name="$1"
    local marketplace_location

    marketplace_location="$(
        claude plugin marketplace list --json |
            jq --exit-status --raw-output \
                --arg marketplace_name "${marketplace_name}" \
                '.[] | select(.name == $marketplace_name) | .installLocation'
    )"
    printf '%s/.claude-plugin/marketplace.json\n' "${marketplace_location}"
}

function install_or_update_claude_plugin() {
    local plugin_identifier="$1"
    local installed_plugins="$2"

    if jq --exit-status \
        --arg plugin_identifier "${plugin_identifier}" \
        'any(.[]; .id == $plugin_identifier)' \
        <<<"${installed_plugins}" >/dev/null; then
        claude plugin update "${plugin_identifier}"
    else
        claude plugin install "${plugin_identifier}"
    fi
}

function install_motlin_claude_plugins() {
    local installed_plugins
    local marketplace_manifest
    local plugin_identifier
    local plugin_name

    ensure_claude_marketplace \
        "motlin-claude-code-plugins" \
        "motlin/claude-code-plugins"
    marketplace_manifest="$(claude_marketplace_manifest "motlin-claude-code-plugins")"
    installed_plugins="$(claude plugin list --json)"

    while IFS= read -r plugin_name; do
        plugin_identifier="${plugin_name}@motlin-claude-code-plugins"
        install_or_update_claude_plugin "${plugin_identifier}" "${installed_plugins}"
    done < <(
        jq --exit-status --raw-output \
            '.plugins[].name | select(. != "iterm2-titles")' \
            "${marketplace_manifest}"
    )
}

function install_official_claude_plugins() {
    local installed_plugins
    local plugin_identifier
    local plugin_name
    local plugin_names=(
        chrome-devtools-mcp
        claude-md-management
        code-simplifier
        hookify
        plugin-dev
        skill-creator
        typescript-lsp
    )

    ensure_claude_marketplace \
        "claude-plugins-official" \
        "anthropics/claude-plugins-official"
    installed_plugins="$(claude plugin list --json)"

    for plugin_name in "${plugin_names[@]}"; do
        plugin_identifier="${plugin_name}@claude-plugins-official"
        install_or_update_claude_plugin "${plugin_identifier}" "${installed_plugins}"
    done
}

function ensure_codex_marketplace() {
    local marketplaces
    local source_type

    marketplaces="$(codex plugin marketplace list --json)"
    source_type="$(
        jq --raw-output \
            --arg marketplace_name "motlin-claude-code-plugins" \
            '.marketplaces[]
            | select(.name == $marketplace_name)
            | .marketplaceSource.sourceType // "managed"' \
            <<<"${marketplaces}"
    )"

    if [[ -z "${source_type}" ]]; then
        codex plugin marketplace add "motlin/claude-code-plugins"
    elif [[ "${source_type}" == "git" ]]; then
        codex plugin marketplace upgrade "motlin-claude-code-plugins"
    else
        echo "Using existing Codex motlin-claude-code-plugins ${source_type} marketplace."
    fi
}

function install_motlin_codex_plugins() {
    local plugin_catalog
    local plugin_identifier

    ensure_codex_marketplace
    plugin_catalog="$(
        codex plugin list \
            --marketplace "motlin-claude-code-plugins" \
            --available \
            --json
    )"

    while IFS= read -r plugin_identifier; do
        codex plugin add "${plugin_identifier}"
    done < <(
        jq --exit-status --raw-output \
            '[.installed[], .available[]]
            | .[]
            | select(.installPolicy == "AVAILABLE")
            | .pluginId' \
            <<<"${plugin_catalog}"
    )
}

function install_shared_skills() {
    local installed_plugins

    ensure_claude_marketplace \
        "skills-curated" \
        "trailofbits/skills-curated"
    installed_plugins="$(claude plugin list --json)"

    install_or_update_claude_plugin \
        "humanizer@skills-curated" \
        "${installed_plugins}"
    install_or_update_claude_plugin \
        "skill-extractor@skills-curated" \
        "${installed_plugins}"

    npx --yes skills add "trailofbits/skills-curated" \
        --global \
        --agent codex \
        --skill humanizer skill-extractor \
        --yes
}

install_motlin_claude_plugins
install_official_claude_plugins
install_motlin_codex_plugins
install_shared_skills
