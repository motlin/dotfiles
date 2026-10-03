#!/usr/bin/env bash

set -euo pipefail

# Run with the IDEs closed; they rewrite templates on exit.

if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 <jetbrains-settings-checkout>" >&2
    exit 1
fi

SOURCE_DIR="$1"
JETBRAINS_DIR="${HOME}/Library/Application Support/JetBrains"

installed=false

# IDE config directories are named like IntelliJIdea2026.2.
for ide_dir in "${JETBRAINS_DIR}"/*[0-9][0-9][0-9][0-9].[0-9]*/; do
    [[ -d "${ide_dir}" ]] || continue

    mkdir -p "${ide_dir}colors" "${ide_dir}templates" "${ide_dir}options"
    cp "${SOURCE_DIR}/Craig_Light.icls" "${SOURCE_DIR}/Craig_Dark.icls" "${ide_dir}colors/"

    # The repository holds bare <template> elements; a template file needs a group.
    {
        echo '<templateSet group="Craig">'
        cat "${SOURCE_DIR}/live-templates.xml"
        echo '</templateSet>'
    } >"${ide_dir}templates/Craig.xml"

    # The IDE owns this whole options file, so only seed it.
    if [[ ! -f "${ide_dir}options/postfixTemplates.xml" ]]; then
        cp "${SOURCE_DIR}/postfixTemplates.xml" "${ide_dir}options/"
    fi

    installed=true
done

if [[ "${installed}" == false ]]; then
    echo "No JetBrains IDE config directories yet; launch each IDE once, then rerun."
fi
