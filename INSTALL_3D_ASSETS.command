#!/bin/bash
# One-click, local-only 3D asset installer. Does not touch workshop records.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
PY=""
for candidate in /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
 if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then PY="$(command -v "$candidate")";break;fi
done
if [ -z "$PY" ]; then echo 'Python 3.10+ required'; read -r -p 'Press Enter to close...' _; exit 2;fi
KIT="$HOME/Downloads/325ix_3d_assets_v1.zip"
if [ -f "$KIT" ]; then
 echo "Installing verified assets from $KIT"
 "$PY" scripts/prepare_3d_assets.py --kit "$KIT" || { echo 'Could not validate the downloaded kit.'; read -r -p 'Press Enter to close...' _; exit 1; }
else
 echo 'No downloaded kit found. Attempting GitHub release download...'
 "$PY" scripts/prepare_3d_assets.py || {
  echo 'Open https://github.com/saleemmbayed-sketch/325ix-restoration-os/releases/tag/rc15-3d-runtime'
  echo 'Download 325ix_3d_assets_v1.zip to Downloads, then run this installer again.'
  read -r -p 'Press Enter to close...' _; exit 1;
 }
fi
echo '3D assets installed. Restart RUN_325IX_3D_STUDIO.command.'
read -r -p 'Press Enter to close...' _
