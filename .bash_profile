# That this file is used by any Bourne-shell derivative to setup the
# environment for login shells.

# source the system wide bashrc if it exists
if [ -e /etc/bash.bashrc ] ; then
  source /etc/bash.bashrc
fi

# source the users bashrc if it exists
if [ -e "${HOME}/.bashrc" ] ; then
  source "${HOME}/.bashrc"
fi


##
# Your previous /Users/Craig/.bash_profile file was backed up as /Users/Craig/.bash_profile.macports-saved_2016-05-27_at_13:49:26
##

# MacPorts Installer addition on 2016-05-27_at_13:49:26: adding an appropriate PATH variable for use with MacPorts.
export PATH="/opt/local/bin:/opt/local/sbin:$PATH"
# Finished adapting your PATH environment variable for use with MacPorts.

