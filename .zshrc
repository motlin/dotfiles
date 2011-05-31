HISTSIZE=1000000
SAVEHIST=1000000
HISTFILE=~/.history
setopt EXTENDED_HISTORY APPEND_HISTORY INC_APPEND_HISTORY SHARE_HISTORY HIST_REDUCE_BLANKS
setopt AUTO_CD EXTENDED_GLOB CORRECT
bindkey -e
                            
# Shell is interactive.  It is okay to produce output at this point,
# though this example doesn't produce any.  Do setup for
# command-line interactivity.

if [[ -e /etc/zshrc ]]; then
	. /etc/zshrc
fi

# Load environment settings from profile.env
if [[ -e ~/.profile.env ]]; then
	. ~/.profile.env
fi

# Load settings that are unique to this host
if [[ -e ~/.profile.host ]]; then
	. ~/.profile.host
fi

if [[ -e ~/.alias ]]; then
	. ~/.alias
fi

# colors for ls, etc.
if [[ -f ~/.dircolors ]]; then
	eval `dircolors -b ~/.dircolors`
fi

stty erase 

# prompt #######################################################################

# Color Variables for Prompt
   BLACK=$'%{\e[00;30m%}'
    GRAY=$'%{\e[01;30m%}'
     RED=$'%{\e[00;31m%}'
    PINK=$'%{\e[01;31m%}'
   GREEN=$'%{\e[00;32m%}'
 L_GREEN=$'%{\e[01;32m%}'
  YELLOW=$'%{\e[00;33m%}'
L_YELLOW=$'%{\e[01;33m%}'
    BLUE=$'%{\e[00;34m%}'
  L_BLUE=$'%{\e[01;34m%}'
  PURPLE=$'%{\e[00;35m%}'
L_PURPLE=$'%{\e[01;35m%}'
    CYAN=$'%{\e[00;36m%}'
  L_CYAN=$'%{\e[01;36m%}'
  L_GRAY=$'%{\e[00;37m%}'
   WHITE=$'%{\e[01;37m%}'

    NONE=$'%{\e[00m%}'
    NORM=$'%{\e[01;00;0m%}'

if [[ "$USER" == "$ME" ]]; then
	export MYCOLOR=$L_YELLOW
else
	export MYCOLOR=$L_PURPLE
fi

export PROMPT="$RED%(3L.+ .)%n$GRAY@$L_BLUE%M$GRAY:$MYCOLOR%/${NONE}
$RED%(?..[%?] )${L_GREEN}$ ${NONE}"
################################################################################

# aliases ######################################################################
alias -g H='| head'
alias -g L="| less"
alias -g T='| tail'
################################################################################

# completion ###################################################################
rationalise-dot() {
  if [[ $LBUFFER = *.. ]]; then
    LBUFFER+=/..
  else
    LBUFFER+=.
  fi
}
zle -N rationalise-dot
bindkey . rationalise-dot

# simple completions
# complete only dirs (or symlinks to dirs in some cases) for certain commands
compctl -g '*(/)' rmdir dircmp
compctl -g '*(-/)' cd chdir dirs pushd

# hosts completion for a few commands
compctl -k hosts ftp lftp ncftp ssh w3m lynx links elinks nc telnet rlogin host
compctl -k hosts -P '@' finger

# manpage comletion
man_glob () {
  local a
  read -cA a
  if [[ $a[2] = -s ]] then
  reply=( ${^manpath}/man$a[3]/$1*$2(N:t:r) )
  else
  reply=( ${^manpath}/man*/$1*$2(N:t:r) )
  fi
}
compctl -K man_glob -x 'C[-1,-P]' -m - 'R[-*l*,;]' -g '*.(man|[0-9nlpo](|[a-z]))' + -g '*(-/)' -- man

# completion for some builtins
compctl -z -P '%' bg
compctl -j -P '%' fg jobs disown
compctl -j -P '%' + -s '`ps -x | tail +2 | cut -c1-5`' wait
compctl -A shift
compctl -c type whence where which
compctl -m -x 'W[1,-*d*]' -n - 'W[1,-*a*]' -a - 'W[1,-*f*]' -F -- unhash
compctl -m -q -S '=' -x 'W[1,-*d*] n[1,=]' -g '*(-/)' - 'W[1,-*d*]' -n -q -S '=' - 'n[1,=]' -g '*(*)' -- hash
compctl -F functions unfunction
compctl -k '(al dc dl do le up al bl cd ce cl cr dc dl do ho is le ma nd nl se so up)' echotc
compctl -a unalias
compctl -v getln getopts read unset vared
compctl -v -S '=' -q declare export integer local readonly typeset                                                                       
compctl -eB -x 'p[1] s[-]' -k '(a f m r)' - 'C[1,-*a*]' -ea - 'C[1,-*f*]' -eF - 'C[-1,-*r*]' -ew -- disable                                           
compctl -dB -x 'p[1] s[-]' -k '(a f m r)' - 'C[1,-*a*]' -da - 'C[1,-*f*]' -dF - 'C[-1,-*r*]' -dw -- enable
compctl -k "(${(j: :)${(f)$(limit)}%% *})" limit unlimit
compctl -l '' -x 'p[1]' -f -- . source
compctl -s '$(setopt 2>/dev/null)' + -o + -x 's[no]' -o -- unsetopt
compctl -s '$(unsetopt)' + -o + -x 's[no]' -o -- setopt
compctl -s '${^fpath}/*(N:t)' autoload
compctl -b bindkey
compctl -c -x 'C[-1,-*k]' -A - 'C[-1,-*K]' -F -- compctl
compctl -x 'C[-1,-*e]' -c - 'C[-1,-[ARWI]##]' -f -- fc
compctl -x 'p[1]' - 'p[2,-1]' -l '' -- sched
compctl -x 'C[-1,[+-]o]' -o - 'c[-1,-A]' -A -- set
################################################################################

# color stderr red
# exec 2>>(while read line; do
  # print '\e[91m'${(q)line}'\e[0m' > /dev/tty; done &)
