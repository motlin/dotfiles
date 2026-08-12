#!/usr/bin/env bash

set -euo pipefail

for required_command in claude codex gh jq npx python3; do
    if ! command -v "${required_command}" >/dev/null 2>&1; then
        echo "${required_command} is required to install agent plugins and skills." >&2
        exit 1
    fi
done

BASEDIR="$(command cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly BASEDIR
readonly MOTLIN_MARKETPLACE="motlin-claude-code-plugins"
mapfile -t TITLE_PLUGIN_NAMES < <(jq -r '.titlePluginNames[]' "${BASEDIR}/install-agent-tools.config.json")

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
        # Local marketplaces do not refresh.
        echo "Migrating Codex motlin-claude-code-plugins from ${source_type} source to git." >&2
        codex plugin marketplace remove "motlin-claude-code-plugins"
        codex plugin marketplace add "motlin/claude-code-plugins"
    fi
}

function install_motlin_codex_plugins() {
    local plugin_catalog
    local plugin_identifier
    local plugin_name
    local title_plugin_identifiers=()

    for plugin_name in "${TITLE_PLUGIN_NAMES[@]}"; do
        title_plugin_identifiers+=("${plugin_name}@${MOTLIN_MARKETPLACE}")
    done

    ensure_codex_marketplace
    plugin_catalog="$(
        codex plugin list \
            --marketplace "${MOTLIN_MARKETPLACE}" \
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
            | .pluginId
            | select(IN($ARGS.positional[]) | not)' \
            --args "${title_plugin_identifiers[@]}" \
            <<<"${plugin_catalog}"
    )
}

function install_shared_skills() {
    npx --yes skills add "trailofbits/skills-curated" \
        --global \
        --agent codex \
        --skill humanizer skill-extractor \
        --yes
}

function install_github_stack_tools() {
    local agent
    local GH_HOST="github.com"

    export GH_HOST

    gh extension install github/gh-stack --force

    for agent in claude-code codex; do
        gh skill install github/gh-stack gh-stack \
            --agent "${agent}" \
            --scope user \
            --force
    done
}

# Sourcing the script exposes the functions without installing anything.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    "${BASEDIR}/sync-claude-plugins.py"
    install_motlin_codex_plugins
    install_shared_skills
    install_github_stack_tools
fi
