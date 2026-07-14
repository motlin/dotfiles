# Prevent Terminal.app from maintaining a competing per-session history file.
export SHELL_SESSION_HISTORY=0

# Enforce unique PATH entries globally
typeset -U path

# Smart PATH functions (idempotent)
path_prepend() {  # Add to front (high priority)
  case ":${PATH}:" in
    *:"$1":*) ;;  # Already in PATH
    *) export PATH="$1:$PATH" ;;
  esac
}

path_append() {  # Add to back (low priority)
  case ":${PATH}:" in
    *:"$1":*) ;;  # Already in PATH
    *) export PATH="$PATH:$1" ;;
  esac
}

# Force our bin directories to the front, in order. Unlike path_prepend this
# reorders entries that are already present, so it must be re-run after direnv
# and oh-my-zsh have had a chance to shuffle PATH. -g is required: a bare
# typeset here would declare a function-local path and never touch the real one.
path_enforce_order() {
  typeset -gU path
  path=("$HOME/.bin" "$HOME/.local/bin" $path)
}

set -o allexport
if [ -f "$HOME/.env" ]; then
  source "$HOME/.env"
fi

if [ -f "$HOME/.env.local" ]; then
  source "$HOME/.env.local"
fi

if [ -f "$HOME/.secrets.local" ]; then
  source "$HOME/.secrets.local"
fi
set +o allexport
