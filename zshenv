set -o allexport
if [ -f "$HOME/.env" ]; then
  source "$HOME/.env"
fi

if [ -f "$HOME/.env.local" ]; then
  source "$HOME/.env.local"
fi
set +o allexport
