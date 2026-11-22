#!/bin/bash
# Portable, local-first studio runner. Never overwrites original owner DB.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=""
for candidate in /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
 if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then PY="$(command -v "$candidate")";break;fi
done
if [[ -z "$PY" ]]; then echo "Requires Python 3.10+ (python.org download)." >&2;exit 2;fi
exec "$PY" "$HERE/launch_rc12_trial.py" "$@"
