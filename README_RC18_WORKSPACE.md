# RC18 · Integrated restoration workspace

This is a **local-first user-experience revision** of RC17. It preserves the existing Python/SQLite APIs, garage missions, personal model library, Three.js and hosted E30 preview, catalog evidence, work orders, and safety boundaries. It adds no runtime libraries.

## Launch on Mac

1. Extract this ZIP into a new folder; do not replace existing workshop data.
2. Right-click **RUN_325IX_3D_STUDIO.command** → **Open**. Python 3.10+ is required.
3. The launcher creates/uses a separate `rc12_trial_state` SQLite copy and opens the local page. Do not use an older browser tab if the launcher reports a different port.
4. The existing online four-door E30 reference requires internet. Local 3D uses the separate, licensed RC15 asset kit; OEM diagrams work without it.

## What changed

- A compact dark navigation rail with 6 primary tasks; 4 research/specialist tools remain under Advanced.
- Global catalog search from any screen (`Command + K` on Mac, `Ctrl + K` elsewhere). A search opens Parts & drawings directly.
- Garage home provides 4 task routes, 21 prioritized systems, the full 805 indexed assemblies, actual mission count, and an explicit NOT APPROVED clearance.
- Mission creation is an opt-in, expandable form. Existing missions resume from Garage.
- Mission view leads with steps, next actions, blockers and evidence; inspection, checkpoints, repairs and AI review are expandable.
- Parts search **groups the same BMW part number** while retaining every raw catalog occurrence/date/assembly under its card. No source records are discarded.
- Opening a component directly from the 3D workflow now also opens its parent OEM assembly and part dossier; inspection-job and case-grounded AI actions prefill component context.
- Mobile sidebar, keyboard focus visibility, consistent cards/spacing, and responsive layout.

## Measured and verified

- 10 former top tabs → 6 primary navigation actions + 4 advanced; all original pages remain accessible.
- 805 total catalog assemblies visible vs the previous Garage metric of 344 priority-domain assemblies (the latter was misleading as a full-catalog total).
- Browser-level checks on 1500×1000 desktop and 390×844 mobile: navigation, expandable mission form, cross-screen search, grouped parts, and mobile navigation all passed without JS page errors, using real locally retrieved API fixtures.
- Direct part dossier → parent assembly → prefilled inspection job passed as an isolated browser test.
- Existing `test_mvp_integration.py`, `test_rc12_launcher.py`, `test_rc17_models.py`, and `test_viewer3d_contract.py` passed.

### Limits / still open

- A hosted Sketchfab reference may be blocked by a corporate browser/network; local 3D and OEM mode remain separate. No third-party assets have been copied into GitHub.
- Actual 3D bonnet opening, full M20 assembly meshes, and exact iX AWD exploded mechanical geometry are **next checkpoint**, not part of RC18.
- The user-specific Mac Monterey visual/keyboard acceptance and a real mechanic's end-to-end usability study are still needed. Do not interpret synthetic browser smoke tests as physical fitment or workshop-device certification.
- No safety clearance, torque, or exact variant compatibility is inferred from model geometry, catalog results, or AI answers.

## Quick checks

```bash
python3 test_rc18_ux_contract.py
python3 test_viewer3d_contract.py
python3 test_mvp_integration.py
python3 test_rc17_models.py
```

GitHub: https://github.com/saleemmbayed-sketch/325ix-restoration-os
