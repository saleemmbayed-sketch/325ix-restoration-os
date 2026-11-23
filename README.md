# BMW 325iX Restoration OS — interactive 3D workshop studio

Public source, private-data, local-first **1988 Swiss ECE BMW E30 325iX** restoration assistant. One application brings together a real E30 visual reference, the documented BMW parts/diagram index, persistent evidence-led missions, repair-first decision records, optional local Ollama assistance and QA gates. **No part fitment, vehicle condition or roadworthiness is certified by software.**

## Working application

The existing RC13 Python workbench is preserved, with an additive Three.js/GLB viewer integration: orbit/zoom, pickable reference meshes, camera views, illustrative explode slider, approximate iX subsystem focus, a reliable diagram/callout fallback, and linked catalog dossiers and restoration workflows. A front-axle/steering selection can now carry its visual locator and a validated catalog occurrence into the existing seven-step front-wheel-play case; both remain references until physical evidence confirms the installed part. The full-car model is a **BMW M3 E30 reference, not an accurate 325iX four-door mechanical twin**. See [3D asset provenance](docs/3D_ASSETS.md).

## Quick local test — no Drive data required

For the **full RC21 V4 product trial**, sync the private V4 folder and run
`bash RUN_RC21_FULL.command --v4-root "/absolute/path/to/14_MULTIMODAL_MEDIA_AND_GRAPH"`.
The launcher checks the complete 805-assembly/13,845-row catalog, makes a one-time
copy of the existing workshop jobs into `rc21_full_trial_state`, and opens the
mechanical 3D studio. Run `python3 scripts/prepare_3d_assets.py` first if the
Three.js kit is absent. `/api/v4/status`, `/api/catalog/coverage`, and
`/api/evidence/coverage` report what is actually connected. Existing trial jobs
are resumed on later launches; the original job database remains untouched.
The AI mechanic additionally requires a running Ollama model and
`--ollama-model MODEL`. This is a trial, with safety sign-off still pending.

To create a self-contained test ZIP from this checkout, run `python3 scripts/build_local_test_bundle.py`; extract `out/325ix-restoration-os-local-test.zip` and run `python3 scripts/run_local_demo.py` (or `bash RUN_LOCAL_DEMO.command` on macOS). It requires Python 3.10+ only and uses a five-assembly, seven-row fixture with `DEMO-*` part numbers. The bundle includes pinned local renderer modules and three original illustrative mechanical scenes; it excludes the private Drive mirror, SQLite/workshop state, owner photos, private registries, and the unverified M3 reference model. The UI keeps a visible synthetic-demo warning and binds to loopback. See [Local Test Guide](docs/LOCAL_TEST_GUIDE.md).

Run the isolated API/persistence test with `python3 test_local_demo.py`. This synthetic demo tests the UI and workflow only; it is not the 805-assembly V4 catalog, a fitment source, a repair manual, or a safety approval. To test the full catalog, use the private V4/RC13 setup below.

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

The existing Drive V4 folder can also supply the read-only catalog directly, without building a second catalog database. After syncing the `14_MULTIMODAL_MEDIA_AND_GRAPH` folder to the Mac, launch with its local path:

```bash
python3 app.py --v4-root "$HOME/Desktop/14_MULTIMODAL_MEDIA_AND_GRAPH"
```

The app resolves `04_SEARCH/325ix_multimodal.sqlite3` inside that folder, runs SQLite's read-only quick check, validates the expected 805 assemblies and 13,845 part rows, and reads the manifest and any local diagram binaries in place. `/api/v4/status` reconciles manifest records with catalog asset IDs/metadata and checks every reported local download's contained path, required byte count, SHA-256, content signature, file extension, and manifest MIME. Search and assembly responses mark a drawing locally available only when those checks pass; the image endpoint serves only the same verified bytes. The V4 source files are never rewritten. A missing or partial local image pack is reported as incomplete, not as complete because Drive lists files. If the V4 database is absent, the legacy `data/325ix_assemblies.sqlite3` remains the fallback. Catalog diagrams are references, not vehicle-confirmed fitment; actual-part identity and physical photos must remain explicit.

### Test the working UI in an isolated browser preview

With the V4 folder synced as above, run:

```bash
python3 scripts/preview_server.py
```

Open Arena’s **Live Preview** for port 8080 and wait for the workspace to load. In the left navigation, expand **Research & advanced tools → Front axle pilot**. Choose a corner, describe only an observed symptom, and start a case. In a checkpoint, choose `OBSERVED`, enter a finding and its source, and save it. Click **Refresh**, then **Resume inspection** to confirm the checkpoint remains; use **Export work order** to inspect the generated record. Next, open **Explore vehicle → Front axle**, select a modeled component, and try **Isolate in 3D**, **See OEM drawings**, and the catalog-to-inspection handoff. In **Parts & drawings**, keep supplier-image references distinct from the actual-part photo section: there are currently no owner/workshop part photos indexed.

The proxy is the only `0.0.0.0` listener; the Workbench backend keeps its loopback-only host checks. Jobs and any uploaded photos live in a disposable temporary directory; machine VIN variables and the private manual index are not exposed. Stop the preview with Ctrl+C; all preview-created state is discarded. Do not enter real vehicle identifiers or rely on sandbox entries as repair advice. This is an interactive test build—not durable storage, device acceptance, or release sign-off. Please report the browser/device, the exact route and action, and anything confusing, clipped, unresponsive, or lost. The safety banner intentionally remains **NOT APPROVED**.

`python3 test_viewer3d_contract.py` checks offline JS/API integration contracts; `python3 test_front_play_visual_handoff.py` verifies the front-axle visual-to-seven-step case link against both catalog schemas using isolated fixtures; `python3 test_runtime_catalog_paths.py` covers V4-only startup path discovery and legacy fallback; `python3 test_v4_runtime_integrity.py` covers path containment, required size/SHA-256/MIME checks, verified-only HTTP diagram delivery, and manifest/database reconciliation. `python3 release_check_rc14.py --v4-root /path/to/14_MULTIMODAL_MEDIA_AND_GRAPH` runs the catalog integration gate against the supplied private V4 folder and refreshes an ignored local status receipt; it still reports device and mechanical gates separately. The release receipt also auto-detects the repository's local V4 mirror. The legacy `release_check.py` continues to report RC13 checks only. None of these checks constitutes real browser/device acceptance.

## Architecture and evidence

The system remains local-first: application APIs and mutable SQLite mission records are separate from the read-only V4 multimodal research graph, technical source registries, and repair/QA gates. Browser 3D assets are served only via explicit local file allowlists. Original Drive source-of-truth records remain unchanged. See [blueprint](PRODUCT_BLUEPRINT.md), [migrate to GitHub](docs/GITHUB_MIGRATION.md), and [asset rights](docs/3D_ASSETS.md).

### Curated exact-number source reviews

`curated_evidence.json` is an active source-provenance overlay, **not** a VIN-fitment, engineering-specification, component-condition, or safety approval dataset. Its legacy `verified_count` field is retained for compatibility; `count_semantics` and `scope` define the actual meaning. The V40 Drive snapshot declares 173 records. The conservative importer activates 85: it requires a matching explicit `part_number`, row-level `evidence_status`, a parseable explicit `reviewed_utc` or `reviewed_at`, and an HTTPS source with its own status. It preserves eligible V40 records verbatim, retains local-only records, refuses conflicting dossiers, checks every snapshot key against the 7,190-number registry and (when supplied) the V4 catalog, and never edits the source snapshot. The 15 explicit `reviewed_at` timestamps stay in that field; no identity or timestamp is synthesized. Of the 173 input records, 76 are excluded for lacking row-level evidence status, and a further 12 status-bearing rows lack both an explicit matching part number and an accepted review timestamp. Supplier images remain attributed references, not photos of parts installed on this vehicle. The current local `part_photos.sqlite3` has 0 records; the V4 coverage report says 0 workshop photos indexed and 0 unmatched, and its Drive `part_photos.jsonl` / `unmatched_photos.jsonl` artifacts are empty. No catalog diagram or supplier image is substituted for as-found evidence.

To repeat the import from the privately synced V40 files:

```bash
python3 scripts/import_curated_evidence_snapshot.py \
  google_drive/CURATED_EVIDENCE_V40.json \
  --multimodal-db google_drive/14_MULTIMODAL_MEDIA_AND_GRAPH/04_SEARCH/325ix_multimodal.sqlite3
python3 test_curated_evidence_import.py
```

The local V40 snapshot and catalog remain excluded from Git. The imported overlay is a verbatim subset of 85 V40 records, including all 23 prior local entries; the 62-record increase reflects structured source review, not 62 newly certified fitments.

## Current gate

**Source-integrated candidate, not a validated workshop release.** End-to-end catalog/mission regression may pass in sandbox while GLB asset retrieval, Mac Monterey WebGL, real hardware UX, owner device backup/restore, verified 325iX geometry, and mechanical safety sign-off remain independently unverified.

## Public repository privacy

This public source repository intentionally omits the owner's actual VIN/engine number, local workshop state, private Drive folder IDs, licensed third-party binary assets and manuals. At runtime, set optional local environment variables `BMW_325IX_VIN` and `BMW_325IX_ENGINE_NUMBER` to show a specific car's identifiers. Do not commit these values. The original RC13 ZIP and all owner data stay private; `scripts/import_runtime_from_rc13.py` verifies permitted runtime assets locally.

## RC14.1 — 3D module setup and 2D fallback repair

RC14.1 fixes the blank SVG fallback caused by the SVG `hidden` attribute, automatically selects the first cached catalog drawing when 3D assets are unavailable, and checks the complete local Three.js import graph before dynamic import. The launcher retries incomplete installs; the model installer has CDN mirrors. The owner Mac/WebGL signoff is still pending; see [Issue #1](https://github.com/saleemmbayed-sketch/325ix-restoration-os/issues/1).
