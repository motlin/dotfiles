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
readonly CLAUDE_MARKETPLACE_SPECS=(
    "caveman|motlin/caveman|caveman"
    "claude-reflect-marketplace|bayramannakov/claude-reflect|claude-reflect"
    "glebis-skills|glebis/claude-skills|daydream"
    "mattpocock|mattpocock/skills|mattpocock-skills"
    "skills-curated|trailofbits/skills-curated|humanizer skill-extractor"
    "claude-plugins-official|anthropics/claude-plugins-official|chrome-devtools-mcp claude-md-management code-simplifier context7 frontend-design hookify imessage plugin-dev skill-creator typescript-lsp"
)
# Provisioning helpers populate these registries so pruning follows the actual install paths.
CLAUDE_MANAGED_MARKETPLACES=()
CLAUDE_DESIRED_PLUGIN_IDENTIFIERS=()
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

    CLAUDE_MANAGED_MARKETPLACES+=("${marketplace_name}")

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

    CLAUDE_DESIRED_PLUGIN_IDENTIFIERS+=("${plugin_identifier}")

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

function prune_unmanaged_claude_plugins() {
    local installed_plugins
    local managed_marketplaces
    local plugin_identifier
    local updated_settings

    if ((${#CLAUDE_MANAGED_MARKETPLACES[@]} == 0)); then
        return
    fi
    if ((${#CLAUDE_DESIRED_PLUGIN_IDENTIFIERS[@]} == 0)); then
        return
    fi

    managed_marketplaces="$(
        jq -c -n '$ARGS.positional' \
            --args "${CLAUDE_MANAGED_MARKETPLACES[@]}"
    )"
    installed_plugins="$(claude plugin list --json)"

    while IFS= read -r plugin_identifier; do
        if [[ "${CLAUDE_PLUGIN_PRUNE_DRY_RUN:-}" == "1" ]]; then
            printf 'Would uninstall Claude plugin %s.\n' "${plugin_identifier}"
        else
            claude plugin uninstall \
                --prune \
                --yes \
                --scope user \
                "${plugin_identifier}"
            forget_claude_plugin "${plugin_identifier}"
        fi
    done < <(
        jq --raw-output \
            --argjson managed_marketplaces "${managed_marketplaces}" \
            '.[]
            | select(.scope == "user")
            | .id
            | select(
                (split("@")[-1] | IN($managed_marketplaces[]))
                and (IN($ARGS.positional[]) | not)
            )' \
            --args "${CLAUDE_DESIRED_PLUGIN_IDENTIFIERS[@]}" \
            <<<"${installed_plugins}"
    )

    if [[ ! -f "${CLAUDE_SETTINGS_FILE}" ]]; then
        return
    fi

    if [[ "${CLAUDE_PLUGIN_PRUNE_DRY_RUN:-}" == "1" ]]; then
        while IFS= read -r plugin_identifier; do
            printf 'Would remove Claude enabledPlugins key %s.\n' "${plugin_identifier}"
        done < <(
            jq --raw-output \
                --argjson managed_marketplaces "${managed_marketplaces}" \
                'if (.enabledPlugins? | type) == "object"
                then .enabledPlugins
                    | keys[]
                    | select(
                        (split("@")[-1] | IN($managed_marketplaces[]))
                        and (IN($ARGS.positional[]) | not)
                    )
                else empty
                end' \
                "${CLAUDE_SETTINGS_FILE}" \
                --args "${CLAUDE_DESIRED_PLUGIN_IDENTIFIERS[@]}"
        )
        return
    fi

    updated_settings="$(
        jq --argjson managed_marketplaces "${managed_marketplaces}" \
            'if (.enabledPlugins? | type) == "object"
            then .enabledPlugins |= with_entries(
                select((
                    (.key | split("@")[-1] | IN($managed_marketplaces[]))
                    and (.key | IN($ARGS.positional[]) | not)
                ) | not)
            )
            else .
            end' \
            "${CLAUDE_SETTINGS_FILE}" \
            --args "${CLAUDE_DESIRED_PLUGIN_IDENTIFIERS[@]}"
    )"
    rewrite_claude_settings "${updated_settings}"
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

function sync_claude_marketplaces() {
    local installed_plugins
    local marketplace_spec
    local name
    local -a name_array
    local plugin_identifier
    local plugin_name
    local names
    local source

    for marketplace_spec in "${CLAUDE_MARKETPLACE_SPECS[@]}"; do
        IFS='|' read -r name source names <<<"${marketplace_spec}"
        ensure_claude_marketplace "${name}" "${source}"
    done

    installed_plugins="$(claude plugin list --json)"

    for marketplace_spec in "${CLAUDE_MARKETPLACE_SPECS[@]}"; do
        IFS='|' read -r name source names <<<"${marketplace_spec}"
        read -r -a name_array <<<"${names}"

        for plugin_name in "${name_array[@]}"; do
            plugin_identifier="${plugin_name}@${name}"
            install_or_update_claude_plugin "${plugin_identifier}" "${installed_plugins}"
        done
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
    install_motlin_claude_plugins
    sync_claude_marketplaces
    install_motlin_codex_plugins
    install_shared_skills
    install_github_stack_tools
    prune_unmanaged_claude_plugins
fi
