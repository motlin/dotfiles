#!/usr/bin/env bash

set -euo pipefail

for required_command in claude codex gh jq npx; do
    if ! command -v "${required_command}" >/dev/null 2>&1; then
        echo "${required_command} is required to install agent plugins and skills." >&2
        exit 1
    fi
done

readonly CLAUDE_SETTINGS_FILE="${HOME}/.claude/settings.json"
readonly MOTLIN_MARKETPLACE="motlin-claude-code-plugins"
# shellcheck disable=SC2034
readonly CLAUDE_MARKETPLACE_SPECS=(
    "caveman|motlin/caveman|caveman"
    "claude-reflect-marketplace|bayramannakov/claude-reflect|claude-reflect"
    "glebis-skills|glebis/claude-skills|daydream"
    "mattpocock|mattpocock/skills|mattpocock-skills"
    "skills-curated|trailofbits/skills-curated|humanizer skill-extractor"
    "claude-plugins-official|anthropics/claude-plugins-official|chrome-devtools-mcp claude-md-management code-simplifier context7 frontend-design hookify imessage plugin-dev skill-creator typescript-lsp"
)
readonly TITLE_PLUGIN_NAMES=(
    ghostty-titles
    iterm2-titles
    tmux-titles
)

function rewrite_claude_settings() {
    local updated_settings="$1"
    local temporary_file

    temporary_file="$(mktemp "${CLAUDE_SETTINGS_FILE}.agent-tools.XXXXXX")"
    cp -p "${CLAUDE_SETTINGS_FILE}" "${temporary_file}"
    printf '%s\n' "${updated_settings}" >"${temporary_file}"

    if cmp -s "${CLAUDE_SETTINGS_FILE}" "${temporary_file}"; then
        rm -f -- "${temporary_file}"
    else
        mv "${temporary_file}" "${CLAUDE_SETTINGS_FILE}"
    fi
}

# Claude only loads a plugin when settings.json enables it, so a freshly
# installed plugin stays dark until its key exists. Existing keys are left
# alone, including deliberate false values.
function enable_claude_plugin() {
    local plugin_identifier="$1"
    local updated_settings

    if [[ ! -f "${CLAUDE_SETTINGS_FILE}" ]]; then
        return
    fi

    updated_settings="$(
        jq --arg plugin_identifier "${plugin_identifier}" \
            'if (.enabledPlugins? | type) == "object"
                and (.enabledPlugins | has($plugin_identifier))
            then .
            else .enabledPlugins[$plugin_identifier] = true
            end' \
            "${CLAUDE_SETTINGS_FILE}"
    )"
    rewrite_claude_settings "${updated_settings}"
}

# Claude reinstalls any plugin still named in enabledPlugins, whatever the
# value, so uninstalling without dropping the key resurrects the plugin on the
# next startup.
function forget_claude_plugin() {
    local plugin_identifier="$1"
    local updated_settings

    if [[ ! -f "${CLAUDE_SETTINGS_FILE}" ]]; then
        return
    fi

    updated_settings="$(
        jq --arg plugin_identifier "${plugin_identifier}" \
            'if (.enabledPlugins? | type) == "object"
            then del(.enabledPlugins[$plugin_identifier])
            else .
            end' \
            "${CLAUDE_SETTINGS_FILE}"
    )"
    rewrite_claude_settings "${updated_settings}"
}

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

    # Directory-sourced marketplaces do not refresh.
    echo "Migrating Claude ${marketplace_name} from ${source_type} source to github ${marketplace_source}." >&2
    # Claude may refuse removal while marketplace plugins remain installed.
    if ! claude plugin marketplace remove "${marketplace_name}"; then
        uninstall_claude_marketplace_plugins "${marketplace_name}"
        claude plugin marketplace remove "${marketplace_name}"
    fi
    claude plugin marketplace add "${marketplace_source}"
}

function uninstall_claude_marketplace_plugins() {
    local marketplace_name="$1"
    local plugin_identifier

    while IFS= read -r plugin_identifier; do
        claude plugin uninstall \
            --prune \
            --yes \
            --scope user \
            "${plugin_identifier}"
    done < <(
        claude plugin list --json |
            jq --raw-output \
                --arg marketplace_name "@${marketplace_name}" \
                '.[] | .id | select(endswith($marketplace_name))'
    )
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

    enable_claude_plugin "${plugin_identifier}"
}

function uninstall_stale_claude_plugins() {
    local installed_plugins
    local plugin_identifier
    local plugin_name
    # /code-review ships with Claude itself, so the plugin only duplicates it.
    # bash-audit-log and ratchet no longer exist in the marketplace, and the
    # anthropic-agent-skills marketplace is no longer registered, so those
    # plugins can never update. Everything installed should be enabled, so
    # anything left dark belongs here instead.
    local stale_plugin_identifiers=(
        agent-sdk-dev@claude-plugins-official
        bash-audit-log@motlin-claude-code-plugins
        claude-code-setup@claude-plugins-official
        claude-opus-4-5-migration@claude-plugins-official
        code-review@claude-plugins-official
        commit-commands@claude-plugins-official
        document-skills@anthropic-agent-skills
        example-skills@anthropic-agent-skills
        explanatory-output-style@claude-plugins-official
        feature-dev@claude-plugins-official
        github@claude-plugins-official
        learning-output-style@claude-plugins-official
        mcp-server-dev@claude-plugins-official
        playwright@claude-plugins-official
        pr-review-toolkit@claude-plugins-official
        ratchet@motlin-claude-code-plugins
        serena@claude-plugins-official
    )

    for plugin_name in "${TITLE_PLUGIN_NAMES[@]}"; do
        stale_plugin_identifiers+=("${plugin_name}@${MOTLIN_MARKETPLACE}")
    done

    installed_plugins="$(claude plugin list --json)"

    for plugin_identifier in "${stale_plugin_identifiers[@]}"; do
        if jq --exit-status \
            --arg plugin_identifier "${plugin_identifier}" \
            'any(.[]; .id == $plugin_identifier and .scope == "user")' \
            <<<"${installed_plugins}" >/dev/null; then
            claude plugin uninstall \
                --prune \
                --yes \
                --scope user \
                "${plugin_identifier}"
        fi
        forget_claude_plugin "${plugin_identifier}"
    done
}

function install_motlin_claude_plugins() {
    local installed_plugins
    local marketplace_manifest
    local plugin_identifier
    local plugin_name

    ensure_claude_marketplace \
        "${MOTLIN_MARKETPLACE}" \
        "motlin/claude-code-plugins"
    marketplace_manifest="$(claude_marketplace_manifest "${MOTLIN_MARKETPLACE}")"
    installed_plugins="$(claude plugin list --json)"

    while IFS= read -r plugin_name; do
        plugin_identifier="${plugin_name}@${MOTLIN_MARKETPLACE}"
        install_or_update_claude_plugin "${plugin_identifier}" "${installed_plugins}"
    done < <(
        jq --exit-status --raw-output \
            '.plugins[].name | select(IN($ARGS.positional[]) | not)' \
            "${marketplace_manifest}" \
            --args "${TITLE_PLUGIN_NAMES[@]}"
    )
}

function install_official_claude_plugins() {
    local installed_plugins
    local plugin_identifier
    local plugin_name
    local plugin_names=(
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

function install_used_claude_plugins() {
    local installed_plugins

    ensure_claude_marketplace \
        "caveman" \
        "motlin/caveman"
    ensure_claude_marketplace \
        "claude-reflect-marketplace" \
        "bayramannakov/claude-reflect"
    ensure_claude_marketplace \
        "glebis-skills" \
        "glebis/claude-skills"
    ensure_claude_marketplace \
        "mattpocock" \
        "mattpocock/skills"

    installed_plugins="$(claude plugin list --json)"

    install_or_update_claude_plugin \
        "caveman@caveman" \
        "${installed_plugins}"
    install_or_update_claude_plugin \
        "claude-reflect@claude-reflect-marketplace" \
        "${installed_plugins}"
    install_or_update_claude_plugin \
        "daydream@glebis-skills" \
        "${installed_plugins}"
    install_or_update_claude_plugin \
        "mattpocock-skills@mattpocock" \
        "${installed_plugins}"
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
    install_motlin_claude_plugins
    install_official_claude_plugins
    install_used_claude_plugins
    install_motlin_codex_plugins
    install_shared_skills
    install_github_stack_tools
    uninstall_stale_claude_plugins
fi
