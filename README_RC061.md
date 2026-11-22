# BMW E30 325iX Workbench — RC0.6.1: release-blocker patch

**Status: INTERNAL TEST CANDIDATE ONLY — NOT APPROVED FOR WORKSHOP OR ROAD-SAFETY USE.**

This version resolves selected release-gate bugs identified 21 Nov 2026. It does not include the full 7-step Front Axle Expert experience or original BMW manual procedures. Workbench is still a local catalog/inspection research pilot. Original V3/V4 datasets remain read-only.

## Implemented

- Reject unknown vehicle-system codes and assembly/system mismatches before creating a work order.
- Reject non-loopback Host headers and untrusted cross-origin write requests. All write APIs require `X-Workbench-Request: same-origin` and `Content-Type: application/json` from the same-origin UI. No external network listener, default remains `127.0.0.1:8765`. This is a local-only safeguard, not network authentication or a remote security architecture.
- Recompute `catalog/coverage`, `evidence/coverage`, `catalog/worklist` evidence states from the exact-number, source-attributed overlay currently loaded on disk. Later research merges are counted at startup, not from frozen catalog registry statistics.
- Include the 23-record source-reviewed sprint overlay; preserve owner/local existing records on installation with logged collision list.
- Snapshot SQLite job and photo databases consistently, preserve actual photo folder, and back up existing application code before upgrade. Provide one-command application rollback without overwriting later job/photo evidence. No root/sudo.

## Install on Mac Monterey

Stop running Workbench (`Ctrl+C`), extract `325ix_upgrade_rc061` to Desktop. Then:

```bash
bash "$HOME/Desktop/325ix_upgrade_rc061/install_upgrade.sh"
cd "$HOME/Desktop/325ix_workbench"
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 app.py
```

Rollback the application code (stop server first):

```bash
bash "$HOME/Desktop/325ix_workbench/rollback_upgrade.sh"
```

Backup folder `upgrade_backup_rc061_<UTC>` contains code originals and snapshot SQLite database files. Rollback does **not** restore older databases automatically; this prevents deleting new workshop findings added after the installation.

## Tests and acceptance limitation

Run `python3 test_rc061.py` in a disposable copy with its own known valid catalog (not your live workshop database). The release archive contains source code and tests, not the 12 MB original catalog database or 572 copyrighted BMW illustrations. The acceptance report must disclose when test image fixtures are synthetic.

**Still P0-blocked for mechanic-beta:** technically verified BMW procedure/page, actual complete V4 image pack connected to the user's Mac, source-verified physical-part photos and rights, and complete seven-step steering/wheel-play workflow with actual Monterey browser/keyboard validation.
