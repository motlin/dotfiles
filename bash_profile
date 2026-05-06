# shellcheck shell=bash
# That this file is used by any Bourne-shell derivative to setup the
# environment for login shells.

# source the system wide bashrc if it exists
if [ -e /etc/bash.bashrc ]; then
    # shellcheck source=/dev/null
    source /etc/bash.bashrc
fi

# source the users bashrc if it exists
if [ -e "${HOME}/.bashrc" ]; then
    # shellcheck source=/dev/null
    source "${HOME}/.bashrc"
fi
