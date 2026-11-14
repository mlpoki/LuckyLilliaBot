#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
KIND="$(cat "$ROOT/package-kind.txt")"
BASE="$ROOT"
export PATH="$BASE/bin/llbot:$PATH"
"$BASE/bin/llbot/node" "$ROOT/prepare.cjs"
cd "$BASE"
if [ "$KIND" = Desktop ]; then
  exec "$ROOT/LuckyLilliaDesktop.app/Contents/MacOS/LuckyLilliaDesktop"
else
  exec "$BASE/llbot" "--qq-path=$BASE/bin/qq/QQ.app/Contents/MacOS/QQ" "$@"
fi
