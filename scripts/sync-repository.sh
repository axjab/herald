#!/bin/bash

set -euo pipefail

: "${REPOSITORY_URL:?Missing REPOSITORY_URL}"
: "${REPOSITORY_TOKEN:?Missing REPOSITORY_TOKEN}"

DESTINATION=/scripts

if [ ! -d "${DESTINATION}/.git" ]; then
    echo "Cloning repository..."
    git clone --single-branch "https://x-access-token:${REPOSITORY_TOKEN}@${REPOSITORY_URL#https://}" "${DESTINATION}"
else
    echo "Updating repository..."
    git -C "${DESTINATION}" fetch origin
    git -C "${DESTINATION}" reset --hard origin/master
    git -C "${DESTINATION}" clean -fdx
fi
