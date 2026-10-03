#!/usr/bin/env bash

set -euo pipefail

# Copied, not linked, because SteerMouse replaces the file on save.

INSTALLED="${HOME}/Library/Application Support/SteerMouse & CursorSense/Device.smsetting"
BACKUP="${STEERMOUSE_BACKUP:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/config/steermouse/Device.smsetting}"

case "${1:-}" in
    export)
        mkdir -p "$(dirname "${BACKUP}")"
        cp "${INSTALLED}" "${BACKUP}"
        echo "Exported SteerMouse settings to ${BACKUP}"
        ;;
    import)
        if [[ ! -f "${BACKUP}" ]]; then
            echo "No SteerMouse settings at ${BACKUP}; run '$0 export' on a configured Mac first." >&2
            exit 1
        fi
        mkdir -p "$(dirname "${INSTALLED}")"
        cp "${BACKUP}" "${INSTALLED}"
        echo "Imported SteerMouse settings; quit and reopen SteerMouse to load them."
        ;;
    *)
        echo "Usage: $0 <export|import>" >&2
        exit 2
        ;;
esac
