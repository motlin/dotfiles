# Deduplicate PATH and force correct order
typeset -U path
path=("$HOME/.bin" "$HOME/.local/bin" $path)

if [ -f ~/.zprofile.local ]; then
    source ~/.zprofile.local
fi
