#!/usr/bin/env bash

set -euo pipefail

# Idempotent; restarts a process only when one of its domains changed.

ACTIVATE_SETTINGS="${ACTIVATE_SETTINGS:-/System/Library/PrivateFrameworks/SystemAdministration.framework/Resources/activateSettings}"
SET_CURSOR_SCALE="${SET_CURSOR_SCALE:-$(dirname "${BASH_SOURCE[0]}")/set-cursor-scale.py}"
POINTER_SIZE=2.5

# Space-delimited because bash 3.2 has no associative arrays.
changed_domains=" "

write_default() {
    local domain="$1"
    shift
    record_change "${domain}" "" "$@"
}

write_current_host_default() {
    local domain="$1"
    shift
    record_change "${domain}" -currentHost "$@"
}

record_change() {
    local domain="$1"
    local host_flag="$2"
    shift 2
    local before after
    before="$(defaults ${host_flag:+"${host_flag}"} export "${domain}" - 2>/dev/null || true)"
    defaults ${host_flag:+"${host_flag}"} write "${domain}" "$@" || return 1
    after="$(defaults ${host_flag:+"${host_flag}"} export "${domain}" - 2>/dev/null || true)"
    if [[ "${before}" != "${after}" ]]; then
        changed_domains+="${domain} "
    fi
}

domain_changed() {
    [[ "${changed_domains}" == *" $1 "* ]]
}

# A bare function key: no character (65535), keycode, function-key mask (8388608).
function_key_shortcut() {
    printf '<dict><key>enabled</key><true/><key>value</key><dict><key>parameters</key><array><integer>65535</integer><integer>%s</integer><integer>8388608</integer></array><key>type</key><string>standard</string></dict></dict>' "$1"
}

# Keyboard > Function Keys > Use F1, F2, etc. keys as standard function keys
write_default NSGlobalDomain com.apple.keyboard.fnState -bool true

# Trackpad > Tracking speed > Fast
write_default NSGlobalDomain com.apple.trackpad.scaling -float 3

# Trackpad > Tap to click, for built-in and Bluetooth trackpads and the login window
write_default com.apple.AppleMultitouchTrackpad Clicking -bool true
write_default com.apple.driver.AppleBluetoothMultitouch.trackpad Clicking -bool true
write_current_host_default NSGlobalDomain com.apple.mouse.tapBehavior -int 1

# Mouse > Advanced... > Pointer acceleration off
write_default NSGlobalDomain com.apple.mouse.linear -bool true

# Keyboard Shortcuts > Mission Control > Move left/right a space: F14 (107) and F15 (113)
write_default com.apple.symbolichotkeys AppleSymbolicHotKeys -dict-add 79 "$(function_key_shortcut 107)"
write_default com.apple.symbolichotkeys AppleSymbolicHotKeys -dict-add 81 "$(function_key_shortcut 113)"

# Keyboard Shortcuts > Spotlight > Show Spotlight search off, freeing Command-Space for Raycast
write_default com.apple.symbolichotkeys AppleSymbolicHotKeys -dict-add 64 '<dict><key>enabled</key><false/><key>value</key><dict><key>parameters</key><array><integer>32</integer><integer>49</integer><integer>1048576</integer></array><key>type</key><string>standard</string></dict></dict>'

# Accessibility > Display > Pointer size (1 to 4); needs Full Disk Access
if ! write_default com.apple.universalaccess mouseDriverCursorSize -float "${POINTER_SIZE}" 2>/dev/null; then
    echo "Skipping pointer size: grant this terminal Full Disk Access and rerun." >&2
fi

# Desktop & Dock > Hot Corners: all off (1 = no action)
for corner in tl tr bl br; do
    write_default com.apple.dock "wvous-${corner}-corner" -int 1
    write_default com.apple.dock "wvous-${corner}-modifier" -int 0
done

# Finder shows hidden files
write_default com.apple.finder AppleShowAllFiles -bool true

# Activity Monitor > View > Dock Icon > Show CPU History (6); applies on next launch
write_default com.apple.ActivityMonitor IconType -int 6

if domain_changed com.apple.dock; then
    killall Dock || true
fi

if domain_changed com.apple.finder; then
    killall Finder || true
fi

# The pointer size is otherwise read only at login.
if domain_changed com.apple.universalaccess; then
    "${SET_CURSOR_SCALE}" "${POINTER_SIZE}" || true
fi

# Reloads keyboard, trackpad, mouse, and shortcut settings without logging out.
if domain_changed NSGlobalDomain ||
    domain_changed com.apple.symbolichotkeys ||
    domain_changed com.apple.AppleMultitouchTrackpad ||
    domain_changed com.apple.driver.AppleBluetoothMultitouch.trackpad; then
    "${ACTIVATE_SETTINGS}" -u || true
fi
