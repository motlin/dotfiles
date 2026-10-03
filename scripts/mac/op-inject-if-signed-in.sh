#!/usr/bin/env bash

set -euo pipefail

# On a fresh Mac the 1Password app has not been opened yet, so the CLI has no account.
# Skip instead of failing so the first install finishes; a rerun after signing in generates the file.

if [[ "$#" -ne 2 ]]; then
    echo "Usage: $0 <template> <output>" >&2
    exit 2
fi

TEMPLATE="$1"
OUTPUT="$2"
BASEDIR="$(command cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly TEMPLATE OUTPUT BASEDIR

if [[ -z "$(op account list 2>/dev/null)" ]]; then
    echo "Warning: 1Password CLI has no account yet, so ${OUTPUT} was not generated." \
        "Turn on Settings > Developer > Integrate with 1Password CLI in the 1Password app," \
        "then rerun ./install mac." >&2
    exit 0
fi

"${BASEDIR}/../run-quietly.sh" op inject --force --in-file "${TEMPLATE}" --out-file "${OUTPUT}"
