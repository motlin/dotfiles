#!/usr/bin/env bash

set -euo pipefail

# IINA opens video, and the audio types that would otherwise open in Music.

IINA_BUNDLE_ID="com.colliderli.iina"

video_extensions=(
    3gp asf avi flv m2ts m4v mkv mov mp4 mpeg mpg mts ogv rm rmvb ts vob webm wmv
)

audio_extensions=(
    aac aif aiff flac m4a mp3 ogg opus wav wma
)

for extension in "${video_extensions[@]}" "${audio_extensions[@]}"; do
    duti -s "${IINA_BUNDLE_ID}" ".${extension}" all
done
