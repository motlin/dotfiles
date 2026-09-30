#!/bin/bash

set -Eeuo pipefail

# Check that there is exactly one argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <message>"
    exit 1
fi

MESSAGE="$1"

echo -e "$MESSAGE"

curl --silent \
    --output /dev/null \
    --form-string "token={{ op://Development/pushover.net/PUSHOVER_TOKEN }}" \
    --form-string "user={{ op://Development/pushover.net/PUSHOVER_USER }}" \
    --form-string "message=$MESSAGE" \
    https://api.pushover.net/1/messages.json
