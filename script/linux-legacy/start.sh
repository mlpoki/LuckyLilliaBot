#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$ROOT/bin/llbot:$PATH"
cd "$ROOT"
exec "$ROOT/llbot" "--qq-path=$ROOT/QQ/qq" "$@"
