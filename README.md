# BMW 325iX Restoration OS — interactive 3D workshop studio

Public source, private-data, local-first **1988 Swiss ECE BMW E30 325iX** restoration assistant. One application brings together a real E30 visual reference, the documented BMW parts/diagram index, persistent evidence-led missions, repair-first decision records, optional local Ollama assistance and QA gates. **No part fitment, vehicle condition or roadworthiness is certified by software.**

## Working application

The existing RC13 Python workbench is preserved, with an additive Three.js/GLB viewer integration: orbit/zoom, pickable reference meshes, camera views, illustrative explode slider, approximate iX subsystem focus, a reliable diagram/callout fallback, and one-click links to actual catalog part dossiers and restoration missions. The provided model is a **BMW M3 E30 reference, not an accurate 325iX four-door mechanical twin**. It is downloaded from a pinned CC BY 4.0 upstream source rather than copied from unlicensed application code. See [3D asset provenance](docs/3D_ASSETS.md).

## Run on an extracted full release

1. Ensure Python 3.10+ is installed.
2. Launch `bash RUN_325IX_3D_STUDIO.command` (or double-click on macOS). The launcher makes an isolated copy of any existing workshop database. If there is none, it creates a fresh isolated one. It can prepare and cache the free licensed 3D dependencies during the first online launch. 2D stays available if installation fails.
3. The local browser opens on `http://127.0.0.1:8765` (or the next free local port).
4. Select **Digital Twin → iX system → drawings/assembly/callout**. Mesh picks never silently assign an OEM identity.

## Run after cloning this GitHub source-only tree

The Git tree deliberately excludes third-party original source archives, immutable generated SQL indexes, local photographs and owner state. Start from the corresponding RC13 ZIP already held in Drive/Library:

```bash
python3 scripts/import_runtime_from_rc13.py /path/to/BMW_325IX_RESTORATION_OS_MVP_20261122_RC13.zip
python3 scripts/prepare_3d_assets.py
bash RUN_325IX_3D_STUDIO.command
```

`python3 test_viewer3d_contract.py` checks offline JS/API integration contracts. `python3 release_check_rc14.py` and `python3 test_mvp_integration.py` require the runtime data import. The legacy `release_check.py` continues to report RC13 checks only. Neither constitutes real browser/device acceptance.

## Architecture and evidence

The existing API, local SQLite mission records, V4 multimodal research graph, technical source registries and repair/QA gates are unchanged. Browser 3D assets are served only via explicit local file allowlists. Original Drive source-of-truth records remain unchanged. See [blueprint](PRODUCT_BLUEPRINT.md), [migrate to GitHub](docs/GITHUB_MIGRATION.md), and [asset rights](docs/3D_ASSETS.md).

## Current gate

**Source-integrated candidate, not a validated workshop release.** End-to-end catalog/mission regression may pass in sandbox while GLB asset retrieval, Mac Monterey WebGL, real hardware UX, owner device backup/restore, verified 325iX geometry, and mechanical safety sign-off remain independently unverified.

## Public repository privacy

This public source repository intentionally omits the owner's actual VIN/engine number, local workshop state, private Drive folder IDs, licensed third-party binary assets and manuals. At runtime, set optional local environment variables `BMW_325IX_VIN` and `BMW_325IX_ENGINE_NUMBER` to show a specific car's identifiers. Do not commit these values. The original RC13 ZIP and all owner data stay private; `scripts/import_runtime_from_rc13.py` verifies permitted runtime assets locally.
