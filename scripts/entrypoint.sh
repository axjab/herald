#!/usr/bin/env bash
set -euo pipefail
echo "Synchronizing scripts..."
sync-repository.sh
echo "Starting Herald..."
exec python3 /app/herald.py
