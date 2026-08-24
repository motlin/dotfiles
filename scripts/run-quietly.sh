#!/usr/bin/env bash

set -uo pipefail

if [[ "$#" -eq 0 ]]; then
    echo "Usage: $0 <command> [argument ...]" >&2
    exit 2
fi

output="$("$@" 2>&1)"
status=$?

if [[ "${status}" -ne 0 && -n "${output}" ]]; then
    printf '%s\n' "${output}" >&2
fi

exit "${status}"
