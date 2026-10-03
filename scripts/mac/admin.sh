#!/usr/bin/env bash

set -euo pipefail

# Settings that need sudo, kept out of ./install mac.

usage() {
    echo "Usage: $0 time-machine <smb://user@host/share>" >&2
    exit 2
}

# -p prompts for the share's password.
set_time_machine() {
    local url="$1"
    if ! sudo tmutil destinationinfo 2>/dev/null | grep -qF "${url}"; then
        sudo tmutil setdestination -a -p "${url}"
    fi
    sudo defaults write /Library/Preferences/com.apple.TimeMachine RequiresACPower -bool true
}

if [[ "$#" -ne 2 ]]; then
    usage
fi

case "$1" in
    time-machine) set_time_machine "$2" ;;
    *) usage ;;
esac
