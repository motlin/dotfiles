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

set -o allexport
if [ -f "$HOME/.env" ]; then
  source "$HOME/.env"
fi

if [ -f "$HOME/.env.local" ]; then
  source "$HOME/.env.local"
fi
set +o allexport
