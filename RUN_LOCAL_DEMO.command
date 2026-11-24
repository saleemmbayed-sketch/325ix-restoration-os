#!/bin/bash
# Start the bundled, synthetic, loopback-only local test workbench.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
    PY="$(command -v "$candidate")"
    break
  fi
done
if [[ -z "$PY" ]]; then
  echo "Requires Python 3.10+ (standard library only)." >&2
  exit 2
fi
exec "$PY" "$HERE/scripts/run_local_demo.py" "$@"
