#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
sudo apt-get update
sudo apt-get install -y xvfb xauth dbus-x11 libgtk-3-0 libnss3 libasound2t64 libgbm1 libxss1 libsecret-1-0 libnotify4
sudo chown root:root "$ROOT/QQ/chrome-sandbox"
sudo chmod 4755 "$ROOT/QQ/chrome-sandbox"
