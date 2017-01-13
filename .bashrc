if [ ! PS1 ]; then
	# Shell is non-interactive.  Be done now
	return
fi

# Shell is interactive.  It is okay to produce output at this point,
# though this example doesn't produce any.  Do setup for
# command-line interactivity.

if [ -e /etc/bashrc ]; then
	. /etc/bashrc
fi

# Load environment settings from profile.env
if [ -e ~/.profile.env ]; then
	. ~/.profile.env
fi

# Load settings that are unique to this host
if [ -e ~/.profile.host ]; then
	. ~/.profile.host
fi

if [ -e ~/.alias ]; then
	. ~/.alias
fi

# bash history configuration
shopt -s histappend
shopt -s cdspell
export HISTCONTROL=erasedups
export HISTSIZE=100000
export PROMPT_COMMAND='history -a'

# Color Variables for Prompt
export    BLACK='\[\e[00;30m\]'
export     GRAY='\[\e[01;30m\]'
export      RED='\[\e[00;31m\]'
export     PINK='\[\e[01;31m\]'
export    GREEN='\[\e[00;32m\]'
export  L_GREEN='\[\e[01;32m\]'
export   YELLOW='\[\e[00;33m\]'
export L_YELLOW='\[\e[01;33m\]'
export     BLUE='\[\e[00;34m\]'
export   L_BLUE='\[\e[01;34m\]'
export   PURPLE='\[\e[00;35m\]'
export L_PURPLE='\[\e[01;35m\]'
export     CYAN='\[\e[00;36m\]'
export   L_CYAN='\[\e[01;36m\]'
export   L_GRAY='\[\e[00;37m\]'
export    WHITE='\[\e[01;37m\]'

export NONE='\[\e[00m\]'
export NORM='\[\e[01;00;0m\]'

# ME is defined in .profile.host
if [[ "$USER" == "$ME" ]]; then
	export MYCOLOR=$L_YELLOW
else
	export MYCOLOR=$L_PURPLE
fi

PROMPT="${RED}\u${GRAY}@${L_BLUE}\H${GRAY}:${MYCOLOR}\w${NONE} \`git symbolic-ref --short HEAD 2> /dev/null\`\n${L_GREEN}\$${NONE} "
TITLEBAR="\[\e]2;\W\a\]"
PS1=$TITLEBAR$PROMPT

stty erase 

source ~/.bash_completion.d/git-completion.bash
source ~/.bash_completion.d/git-flow-completion.bash
