# RC15 — E30 3D Workshop / OEM drawing fallback

## What changed

The previous SVG schematic is deliberately **not used as a visible fallback**. The Digital Twin now opens a large dedicated model canvas when installed, or the first actually cached BMW exploded catalog drawing (with clickable original-number callouts) if the model is unavailable. A separate inspector provides the 21 indexed catalog systems, mission link and rights-aware GLB import.

The renderer is vanilla Three.js (no second React/Vite stack). Camera orbit/zoom, 3/4-front-side-top presets, mesh picking and an **illustrative** explosion slider are present; these are not assertions of 325iX geometry or real part identities.

## Minimal Mac installation

1. Extract into a new folder; keep existing RC14/local workshop data unchanged.
2. Right-click `RUN_325IX_3D_STUDIO.command` -> **Open**. It first attempts to fetch and validate the single licensed asset kit from [GitHub Releases](https://github.com/saleemmbayed-sketch/325ix-restoration-os/releases/tag/rc15-3d-runtime). This is cached for offline use.
3. If a firewall blocks command-line downloads, use Chrome to download `325ix_3d_assets_v1.zip` from the same GitHub release (keep it in Downloads), then right-click `INSTALL_3D_ASSETS.command` -> **Open**. Restart the main launcher.
4. Open **Digital Twin**. Real-model viewing is only accepted when the GLB loads on your machine, you can orbit and zoom, pick a mesh, adjust explosion and open a BMW catalog drawing. The screenshot below is **not** proof of WebGL acceptance.

## Sources, rights, and limits

- GLB: **BMW M3 E30**, Martin Trafas (`TinoD2`), CC BY 4.0 as reported by the open-source Auto Atlas project. Original https://sketchfab.com/3d-models/free-bmw-m3-e30-ac3c7013434e403e8faff87948caf422 ; optimized derivative https://github.com/ahnuchen/auto-atlas . Asset integrity pinned by Git blob `8aaa3daafd53158b63ced92c4c65d520ebce561f`.
- Three.js `0.159.0` and meshoptimizer `0.22.0` are MIT; license files included in the published runtime kit.
- **Not an exact Swiss ECE four-door 325iX model.** The model supports navigation only; OEM drawing/part numbers, as-installed evidence and measured dimensions remain separate. No safety clearance or fitment is implied.
- Data separation: the live SQLite job database, VIN, workshop photographs, copyrighted diagrams, full research corpus and private Drive links never belong in the public GitHub repository.

## Acceptance gates

- Local Playwright DOM integration verifies visible OEM diagram fallback, click-through OEM callouts, inspector and hidden obsolete map.
- Full existing catalog+mission regression remains passing.
- GitHub Actions assembles the real GLB and renderer from pinned public releases, checks the binary model hash and publishes a single verified kit. The kit's actual WebGL rendering on a user's Monterey Mac must be checked physically; no static-contract pass substitutes for that.
