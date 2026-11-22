# RC17 · Free personal 3D proof — BMW 325iX Restoration OS

This release is a **prototype, not a completed BMW 325iX mechanical digital twin**. It uses only existing Python HTTP/SQLite, Three.js and free-hosted Sketchfab 3D; no new frontend framework or paid assets. Safety-critical fitment is **never inferred from a 3D mesh**.

## Start

1. Extract this ZIP into a **new** directory. Do not overwrite a current restoration workbench or its database.
2. On macOS, right-click `RUN_325IX_3D_STUDIO.command` → **Open**. Python 3.10+ required.
3. Open the URL printed by Terminal; select **Digital Twin**. The free four-door E30 hosted 3D reference is the default; it needs internet. If Sketchfab is blocked, click **Open source model** or switch to **OEM drawings** for the real local parts catalog.
4. For optional *offline* E30 M3 3D reference, download the rights-attributed free runtime kit from https://github.com/saleemmbayed-sketch/325ix-restoration-os/releases/tag/rc15-3d-runtime and run `INSTALL_3D_ASSETS.command`. The M3 remains an approximate model, not a 325iX sedan. The launcher no longer attempts asset downloads silently.
5. For a more correct **personal** model, choose `GLB` or **binary** `STL` in the 3D library under Digital Twin. Assign it to **Whole vehicle** or the chosen one of 21 catalog systems, enter original source/creator, then **Save privately & inspect**. The model is saved to `local_models/` alongside this app, with SHA-256 and original source metadata; all personal files are intentionally ignored by Git.

**Supported:** GLB or binary STL, max 30 MB/model. Multi-file glTF, ZIP and STEP need a one-time conversion to GLB (e.g. Blender). External Sketchfab viewer is online only, and does not expose per-mesh IDs to the local catalog. Locally imported models allow mesh picking and illustrative explosion; only authoritative 2D diagrams identify catalog callouts. No automatic OEM mesh mapping or variant approval.

## Free external assets considered

| Candidate | Access / rights | Use |
|---|---|---|
| BMW 3 Series E30 Sedan by Nieve5677, https://sketchfab.com/3d-models/bmw-3-series-e30-sedan-bd0925e21c934a9cbfdb30ccf5584e86 | Free public online viewer, CC BY; 1.3M triangles (performance check needed) | Default **four-door** exterior preview; download file must be supplied by authorized user for offline import |
| E30 M3 reference by Martin Trafas/TinoD2, https://github.com/ahnuchen/auto-atlas | CC BY 4.0, already pinned SHA and separately packaged | Optional offline fallback; 26 meshes, **not** the correct four-door/iX AWD body |
| 1989 325i X Spindle-Strut (Sketchfab E30 collection), https://sketchfab.com/OsamaMaddani/collections/bmw-e30-5eea3c5286de4c58b7de7c2eb48597a5 | Public listing indicates a downloadable model; exact file and rights **not yet examined** | Best lead for actual iX front-axle 3D inspection |
| E30 front strut sample, https://renn.design/products/e30-front-strut-3d-scan | Advertised free; availability varies | Secondary scan, **not** presumed 325iX compatible |
| E30 suspension STEP references, https://automeshclub.com/parts | Free listing; per-asset terms and variant applicability to verify | Additional mechanical reference meshes, converted privately |
| E30 rear differential scan, https://sketchfab.com/3d-models/bmw-e30-410-lsd-rear-differential-v1-09dec653aa4b4c0eb45f3f3159b9a77a | Online scan reference; file purchase appears separate | Visual reference only, ratio/fitment not established |

## Evidence and acceptance (as of RC17)

- Verified by local Python/Node checks: application parses; catalog + missions + persistence + safety regression; 3D contract tests; write protection (invalid slots, malformed model, external Origin); persistent readback of a small binary STL fixture.
- Verified in a Chromium DOM harness with mocked API: four-door iframe mode is exposed, source URL assigned, switches cleanly to OEM drawing mode without JavaScript errors. **The actual external Sketchfab rendering was not verified** because this runner blocks remote/local browser navigation.
- Previously verified by GitHub's WebGL Chromium smoke (RC16): pinned 26-mesh M3 model renders and 21 approximate marker controls route to the same catalog. **The new RC17 personal STL/GLB model display is not real-device-verified.**
- Not yet accepted: end-to-end real four-door local GLB, iX spindle scan availability/download, real 3D axle internals, per-assembly mesh-to-part provenance, original Mac Monterey performance, and the requested 2x user/visual-quality benchmark across **all** categories. Do not report these as complete.

## Data boundary

The source repository contains application code and tests only. It must not receive owner VIN, engine identifiers, private Drive records, workshop job databases, photos, locally imported models or rights-limited manuals. `local_models/`, private catalog SQLite, and actual photo stores remain private. If a model requires user login or checkout to download legally, request the file from the owner rather than circumventing access controls.
