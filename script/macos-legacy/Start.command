#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
KIND="$(cat "$ROOT/package-kind.txt")"
BASE="$ROOT"
if [ "$KIND" = Desktop ]; then
  BASE="$ROOT/LuckyLilliaDesktop.app/Contents/MacOS"
fi
export PATH="$BASE/bin/llbot:$PATH"
"$BASE/bin/llbot/node" "$ROOT/prepare.cjs"
cd "$BASE"
if [ "$KIND" = Desktop ]; then
  exec "$BASE/LuckyLilliaDesktop"
else
  exec "$BASE/llbot" "--qq-path=$BASE/bin/qq/QQ.app/Contents/MacOS/QQ" "$@"
fi
