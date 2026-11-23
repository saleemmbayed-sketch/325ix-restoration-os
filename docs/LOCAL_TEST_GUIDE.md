# Download and test locally

This package supports two modes:

1. **Synthetic local demo** — runs immediately with a five-assembly, seven-row test catalog generated from `fixtures/local_demo_catalog.json`. It needs no Google Drive sync, RC13 ZIP, network access, third-party Python package, or real vehicle data.
2. **Full local workbench** — use the private, authorized V4 folder or RC13 runtime through the existing commands in the main README. The local-test ZIP does not redistribute private catalog/manual/photo data.

## Requirements

- Python 3.10 or newer.
- A current browser (Safari, Firefox, or Chromium-based browser).
- The downloadable bundle includes the original illustrative mechanical scenes and pinned local Three.js/meshoptimizer JavaScript modules with their license files. No Python package install is needed.

The synthetic catalog is intentionally not BMW source data. Every test part number starts with `DEMO-`; no real OEM drawings, repair procedures, fitment claims, or as-installed observations are included. A persistent banner in the UI repeats this warning. The full-car M3 reference asset and the hosted external sedan viewer are omitted from the demo package.

## Start the application

From the extracted bundle folder:

```bash
python3 scripts/run_local_demo.py
```

On macOS, the wrapper is also available:

```bash
bash RUN_LOCAL_DEMO.command
```

The launcher:

- builds and verifies a synthetic SQLite catalog on first run;
- starts the application on `127.0.0.1` only (tries the next port if 8765 is busy);
- opens the local browser at the printed URL;
- stores demo jobs, photos, and the fixture catalog in a separate per-user data directory, not in the downloaded source tree;
- removes any `BMW_325IX_VIN` and `BMW_325IX_ENGINE_NUMBER` environment values for the demo process.

Options:

```bash
python3 scripts/run_local_demo.py --port 8877 --no-browser
python3 scripts/run_local_demo.py --state-dir /tmp/325ix-demo-test
```

Keep the terminal open while using the app; press Ctrl+C to stop it. Demo state persists across restarts. To reset it, stop the app and remove **only the printed demo state directory**. Do not point the demo launcher at an existing workshop database.

## Manual browser smoke test

1. Confirm the orange **LOCAL SYNTHETIC DEMO** banner is visible.
2. Open **Explore vehicle**. The front-axle mechanical scene should load automatically with orbit, zoom, mesh selection, and the **3D assemblies** tab. Switch between engine bay, front axle and AWD driveline. If a static preview appears, read the renderer error shown in the status line and check `/api/3d/status`.
3. Select **Steering tie rod**, choose a catalog result whose number starts `DEMO-`, and save a test case with a clearly fictional symptom.
4. Confirm the case opens with **road clearance NOT APPROVED**. Open its part dossier; all records should remain labeled as synthetic and unverified.
5. Reload the page and confirm the case and visual locator can be resumed.
6. Export a work order if desired. Its test records live only in the per-user demo state folder.

Never enter real VINs, owner identifiers, real repair measurements, or rely on this fixture to identify a real part. The demo can exercise user-interface and persistence paths only.

## Automated checks

The standard-library local demo integration test starts an isolated server, tests catalog search/dossier/case persistence and checks the safety hold remains in place:

```bash
python3 test_local_demo.py
python3 test_runtime_catalog_paths.py
python3 test_front_play_visual_handoff.py
python3 test_viewer3d_contract.py
python3 test_runtime_importer.py
python3 test_curated_evidence_import.py
python3 test_v4_runtime_integrity.py
python3 test_rc18_ux_contract.py
python3 test_rc19_mechanical.py
python3 test_rc12_launcher.py
python3 test_release_check_rc14.py
```

`test_viewer3d_contract.py`, `test_rc18_ux_contract.py`, and `test_rc19_mechanical.py` are static or contract checks; they do not establish browser/WebGL/device acceptance. `test_local_demo.py` verifies isolated synthetic API behavior only. `test_runtime_importer.py` tests the importer against fabricated archives; a real RC13 archive must be located and independently reconciled before importing.

The legacy RC070 installer/rollback regression additionally needs an isolated, disposable pre-RC070 workbench fixture (not the active Mac folder): `python3 test_rc070.py --baseline /path/to/disposable/325ix_workbench`. It writes a QA report in the source checkout, so use a disposable checkout if you need that artifact isolated.

## Test the full, private V4 data (source checkout only)

The downloadable ZIP intentionally omits Google Drive/runtime data. To test the live local catalog, first sync the authorized `14_MULTIMODAL_MEDIA_AND_GRAPH` folder. In this checkout it is under `google_drive/`; on a Mac it may be under `~/Desktop/`:

```bash
V4_ROOT="$PWD/google_drive/14_MULTIMODAL_MEDIA_AND_GRAPH"
# Or set V4_ROOT="$HOME/Desktop/14_MULTIMODAL_MEDIA_AND_GRAPH"
python3 test_mvp_integration.py --v4-root "$V4_ROOT"
python3 release_check_rc14.py --v4-root "$V4_ROOT"
```

The release receipt refreshes an ignored local `3D_RELEASE_STATUS.json`; its owner-device and mechanical safety gates remain open regardless of the source/integration result. The integration test reads the V4 catalog and uses temporary jobs, photos, and manual-fixture databases; it does not write test records into the synced V4 folder or your normal workshop state. To audit the V4 manifest, downloaded diagram bytes, and SQLite catalog through the running app, launch the isolated full-data preview:

```bash
python3 scripts/preview_server.py --v4-root "$V4_ROOT" --port 8081
```

Open the preview at `http://127.0.0.1:8081` and inspect `/api/v4/status`, `/api/catalog/coverage`, and `/api/evidence/coverage`. The preview keeps jobs/photos in a temporary directory and deliberately does not expose the private manual index. In another terminal, optional full-data browser regression (requires Node.js, Playwright, and Chromium):

```bash
NODE_PATH=/path/to/playwright/node_modules \
CHROMIUM_EXECUTABLE_PATH=/path/to/chromium \
WORKBENCH_URL=http://127.0.0.1:8081 \
node scripts/browser_visual_handoff.cjs
```

Stop the preview with Ctrl+C; its temporary test cases and photo state are discarded. To check a synced V40 evidence snapshot without overwriting the active overlay, always send the output to a temporary path:

```bash
VALIDATION_DIR="$(mktemp -d)"
python3 scripts/import_curated_evidence_snapshot.py \
  google_drive/CURATED_EVIDENCE_V40.json \
  --multimodal-db "$V4_ROOT/04_SEARCH/325ix_multimodal.sqlite3" \
  --output "$VALIDATION_DIR/curated_evidence.json"
# After reviewing the report, remove only this temporary directory:
rm -r "$VALIDATION_DIR"
```

The last local V4 audit found 805 assemblies, 13,845 part rows, 7,190 unique part numbers, and 572/572 local image assets hash-verified. A current Drive metadata/content comparison confirmed matching Drive `md5Checksum` values for the synced V4 SQLite database (`e2cf894fa7c2845b172a0e920801405b`, Drive modified `2026-11-21T18:55:47Z`), image manifest (`7d94e8d98c0e4a5cd1923c5a7bcb8a5c`, `2026-11-21T18:55:40Z`), and V40 snapshot (`8874343b3998685c26ac077d61768dae`, `2026-11-23T08:26:42Z`). The V4 database SHA-256 is `9f5ac62a66e9670a72d4e2089db375bbd132ba757918c17f0f037526958c3f71`. All 572 local image bytes also pass their SHA-256 entries in that matching manifest. This does not compare every individual Drive image object’s remote checksum, nor recursively verify every file in every Drive subfolder.

The V40 snapshot has 173 input records, of which 85 pass the importer’s conservative source-review gate; a safe dry run merged 85 into an ephemeral output. The active overlay/API reports those 85 as exact-number source-reviewed (never VIN-fitment approvals). The registry’s embedded `researched_exact_number_records: 19` is a separate per-registry status count: all 19 are in the active 85; the other 66 qualifying overlay reviews still say `NOT_RESEARCHED` inside that registry. Treat the API’s dynamic overlay count and the registry’s stored count as different layers, not equivalent totals.

The manual index currently has 57 documents and 1,562 pages but 0 verified documents / 0 claim records. Actual workshop-photo records remain 0; Drive lists the 02_PART_PHOTOS folder as empty. Re-run the local audits after syncing. Do not treat indexed manuals as verified procedures, or the remote metadata match as a review of source rights, fitment, technical truth, or safety.

Optional Playwright browser regression for the synthetic package (requires Node.js, `playwright`, and Chromium): start the local demo in one terminal, then in another run:

```bash
NODE_PATH=/path/to/playwright/node_modules \
WORKBENCH_URL=http://127.0.0.1:8765 \
node scripts/browser_local_demo_smoke.cjs
```

Set `CHROMIUM_EXECUTABLE_PATH` if Chromium is installed outside Playwright's default cache. This browser test uses only loopback endpoints and blocks the hosted model domain.

## Build a fresh ZIP

From the source checkout, run:

```bash
python3 scripts/build_local_test_bundle.py
```

The ZIP and SHA-256 sidecar are written under `out/`. The packager uses explicit model/vendor allowlists and exclusions; it rejects any archive containing Drive mirrors, SQLite state, owner photos, private registries, the M3 GLB, `.git`, or cache files. The included `LOCAL_TEST_PACKAGE_MANIFEST.json` hashes the files inside the ZIP and records whether the source worktree had uncommitted changes. Verify the outer archive checksum before extracting:

```bash
# macOS
shasum -a 256 -c out/325ix-restoration-os-local-test.zip.sha256
# Linux
sha256sum -c out/325ix-restoration-os-local-test.zip.sha256
```

## What this does not prove

The local demo is not the full 805-assembly/13,845-row V4 catalog and has no 7,190-item registry, OEM image corpus, licensed 325iX body geometry, manual-page archive, or real workshop data. Passing local tests does not close Mac/owner-device acceptance, source-rights and geometry-identity gates, fitment review, independent mechanic sign-off, roadworthiness, or the S1–S7/C0 Drive-to-GitHub mapping. See [evidence reconciliation](EVIDENCE_RECONCILIATION.md) and [delivery tracking](DELIVERY_TRACKING.md).
