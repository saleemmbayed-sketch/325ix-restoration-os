#!/bin/bash
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=""
for candidate in /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' >/dev/null 2>&1; then PYTHON="$(command -v "$candidate")";break;fi
done
if [[ -z "$PYTHON" ]]; then echo 'Python 3.10+ is required.' >&2;exit 2;fi
exec "$PYTHON" "$KIT/launch_rc12_trial.py" "$@"
