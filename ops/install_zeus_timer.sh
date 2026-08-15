#!/usr/bin/env bash

set -e

APP_ROOT="/data3/zcwang/daily-intelligence-hub/app"
UNIT_ROOT="$HOME/.config/systemd/user"

mkdir -p "$UNIT_ROOT"
install -m 0644 "$APP_ROOT/ops/systemd/aix-daily-raw.service" "$UNIT_ROOT/aix-daily-raw.service"
install -m 0644 "$APP_ROOT/ops/systemd/aix-daily-raw.timer" "$UNIT_ROOT/aix-daily-raw.timer"

systemctl --user daemon-reload
systemctl --user enable --now aix-daily-raw.timer
systemctl --user status aix-daily-raw.timer --no-pager
