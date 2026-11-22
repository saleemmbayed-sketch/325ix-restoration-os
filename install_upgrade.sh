#!/bin/bash
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=""
for candidate in /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
 if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)' >/dev/null 2>&1;then PYTHON="$(command -v "$candidate")";break;fi
done
if [[ -z "$PYTHON" ]];then echo 'Python 3.10+ required (use 3.11 on Monterey).' >&2;exit 2;fi
"$PYTHON" -m py_compile "$KIT/app.py" "$KIT/index_manuals.py" "$KIT/upgrade_070.py" "$KIT/rollback_070.py"
exec "$PYTHON" "$KIT/upgrade_070.py" "${1:-$HOME/Desktop/325ix_workbench}"
