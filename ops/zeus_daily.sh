#!/usr/bin/env bash

set -e

APP_ROOT="/data3/zcwang/daily-intelligence-hub/app"
DATA_ROOT="/data3/zcwang/daily-intelligence-hub"

mkdir -p "$DATA_ROOT/raw" "$DATA_ROOT/runtime/site"

/usr/bin/git -C "$APP_ROOT" pull --ff-only origin main
/usr/bin/python3 "$APP_ROOT/backend/daily_digest.py" \
  --site-root "$DATA_ROOT/runtime/site" \
  --raw-root "$DATA_ROOT/raw" \
  --days 3 \
  --limit 16
