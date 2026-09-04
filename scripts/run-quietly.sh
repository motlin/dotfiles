#!/usr/bin/env bash

set -uo pipefail

if [[ "$#" -eq 0 ]]; then
    echo "Usage: $0 <command> [argument ...]" >&2
    exit 2
fi

if [[ "${DOTFILES_INSTALL_VERBOSE:-false}" == true ]]; then
    exec "$@"
fi

output="$("$@" 2>&1)"
status=$?

if [[ "${status}" -ne 0 ]]; then
    printf 'Command failed with exit status %d:' "${status}" >&2
    printf ' %q' "$@" >&2
    printf '\n' >&2

    if [[ -n "${output}" ]]; then
        printf '%s\n' "${output}" >&2
    fi
fi

exit "${status}"
