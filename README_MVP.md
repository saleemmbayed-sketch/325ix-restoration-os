# BMW 325iX Restoration OS — MVP-0.9.0 RC12

This package is a controlled, local system-wide 325iX restoration MVP for VIN `VIN_NOT_CONFIGURED`. It reuses the existing Workbench and research assets and connects them to the real derived multimodal catalog index. Front axle/steering is the first complete proving case, not the product boundary.

## What is working

- Exact catalog search and part dossiers against 805 assemblies and 13,845 part occurrences.
- A system-wide Garage that organizes the priority restoration scope into AWD/drivetrain, suspension/steering, brakes, engine support, transmission/clutch and electrical domains, with climate/visibility queued next.
- Persistent restoration missions that can be started and resumed across every priority domain while sharing the same evidence, safety, work-order and digital-twin contracts.
- A Living Mission workspace that turns each mission into one evidence-stage journey with blockers, progress, evidence counts and contextual actions for parts, procedures, AI, work orders and the vehicle twin.
- Existing V4 graph relationships: 572 image assets, 805 figure occurrences and 13,845 part-to-figure links.
- Three materialized front-axle/steering diagrams served through the UI from the read-only local V4 copy.
- Six specialist roles, seven evidence checkpoints and persistent front-axle cases.
- Evidence ledger for observations, measurements, tools and sources.
- Work-order export, restart recovery and integration-health reporting.
- Grounded offline assistant that identifies evidence gaps and refuses unsupported diagnosis, fitment and safety approval.
- Manual evidence index with page/document hashes, variant scope, authority, market and verification metadata; returned citations remain visibly separate from URL-only pointers.
- Bundled maintenance evidence index: 57 extracted source documents and 1,562 page/section records, including the newly acquired exact 1988 325iX ETM, owner/manual references, AWD service information and repair/rebuild evidence. These are public/community/OES extracts with applicability and rights caveats, not automatically authorized BMW procedures.
- Curated manual-claim conflict detection; unresolved claims are surfaced instead of being silently combined.
- Repair/sourcing comparison ledger with repair-first ordering, evidence requirements and pending-human-decision states.
- Workshop launchpad with live subsystem/evidence status, explicit safety state, RTL Arabic interface direction, selectable Arabic/English AI output, and optional browser dictation/read-aloud controls.
- Persistent vehicle digital twin with separate factory/as-installed/confidence state, auditable evidence events, restart-safe event history and evidence-only XP/level progress; XP never grants fitment or safety approval.
- Unified case cockpit combining job status, checkpoints, evidence, repair/sourcing options, twin events and explicit blockers through one overview contract.
- Specialist intent router for part identity, diagnostics, repair/rebuild, AWD fitment, sourcing and QA; routing returns required evidence and approval gates and is visible before/with AI answers.
- Persistent component-instance registry with location/side/marking/condition, separate fact layers and explicit uncertainty states; component identity remains unconfirmed until evidence supports it.

## Run

```bash
python3 release_check.py
python3 test_mvp_integration.py
python3 app.py
```

Open `http://127.0.0.1:8765`.

The app auto-detects the included real multimodal database, derived local image manifest and bundled `maintenance_manual_index.sqlite3`. The derived `maintenance_web_gap_input/` set and `ingest_web_gap_materials.py` preserve the reproducible text/provenance intake for the newly acquired public materials. Use `--jobs /path/to/workshop_jobs.sqlite3` to keep mutable workshop records outside the release folder. Index additional authorized `.txt`/`.md` text with `index_manuals.py` and start with `--manual-index /path/to/manual_index.sqlite3`. Use `--ollama MODEL` only after a local model has been installed and separately validated.

Before an older job database is migrated, the app creates and integrity-checks a snapshot in `workshop_jobs_backups/`, then records schema version 2. To roll back, stop the app and run `python3 restore_jobs_backup.py --jobs /exact/jobs.sqlite3 --backup /exact/backup.sqlite3 --confirm-replace`; the utility preserves the current database again before replacement and refuses to operate against an active WAL.

For device acceptance, `RUN_RC12_TRIAL.command` clones the current job database into isolated trial state, automatically selects a free local port if an older Workbench is still running, and opens the correct RC12 address in the browser.

## Safety and evidence policy

The release always reports `NOT_APPROVED` for safety clearance. It does not provide torque values, dimensions, tolerances, fitment approval, repair authorization or road-use clearance unless the relevant source text, variant, physical evidence and qualified human sign-off are present. A catalog row is an identity/relationship record, not proof of as-installed fitment.

The original V3/V4 assets and Drive work queues are not overwritten. `image_assets_local.jsonl` is a derived manifest containing only local materialization metadata for the three release-critical diagrams.

## Release evidence

- `RELEASE_STATUS.json` contains the automated gate result and explicit blockers.
- `RELEASE_MANIFEST_MVP.json` records SHA-256 hashes for the release inputs and identifies mutable files excluded from the archive.
- `MVP_PROGRESS.md` contains the product-owner verdict, acceptance matrix and remaining gates.
- `test_mvp_integration.py` exercises real catalog retrieval, page-provenance manual ingestion/search, conflict handling, repair-first options, diagram serving, specialist/workflow APIs, digital-twin events and restart persistence, case persistence, evidence logging, recovery and export.
- Cross-domain integration fixtures exercise AWD/drivetrain and electrical missions in addition to the front-axle proving case.
- The final release gate also checks the bundled maintenance evidence index; browser voice controls are capability-detected and fail back to text without blocking the workflow.

## Not yet workshop-approved

The remaining gates are physical mechanic inspection/sign-off, owner-installed photos and calibrated measurements, authorized page-level model-appropriate repair text, workshop-device UX review, and Arabic voice/Ollama validation. Do not use the software as an independent authority for safety-critical work.
