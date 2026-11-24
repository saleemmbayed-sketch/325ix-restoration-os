# 325iX Front Axle & Steering Expert RC0.7.0 — internal integration pilot

**Not approved for workshop road-safety signoff; not a complete BMW repair procedure.**

This candidate adds a seven-stage, evidence-first front-wheel-play workflow, a linked persistent inspection job, reversible checkpoint entry, exact source references and inline existing BMW 325iX catalog assemblies. It preserves the read-only V3/4 catalog, existing work orders, and local photographs. User-confirmed installed M20B25 is independent from the VIN's factory engine identity.

## Installation (only on an existing Workbench)

1. Stop `python3 app.py` with Ctrl+C. Unpack this archive on Mac Desktop to a folder named `325ix_upgrade_rc070`.
2. Run `bash "$HOME/Desktop/325ix_upgrade_rc070/install_upgrade.sh"`.
3. Launch `cd "$HOME/Desktop/325ix_workbench" && /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 app.py`.
4. Open `http://127.0.0.1:8765`, select **Front Axle Expert**, create a test job, record and reopen a step, and export. This is only an internal test with trained mechanic supervision; do not perform physical vehicle repair based on the software's prompts alone.

Existing data is not overwritten. Additive `expert_case` and `expert_step` tables are initialized in the existing workshop jobs SQLite file and never deleted by rollback. This preserves findings added after upgrade but leaves empty additive tables if code is reverted. A consistent SQLite snapshot is retained as part of the installer backup.

## Rollback

Stop Workbench with Ctrl+C and run `bash "$HOME/Desktop/325ix_workbench/rollback_upgrade.sh"`. Restores app code from pre-RC0.7 backup but **does not revert owner job/photo database** or delete newly logged evidence.

## Connect actual V4 assets

Copy the completed V4 folder `14_MULTIMODAL_MEDIA_AND_GRAPH/` from Drive to Desktop, keeping `03_MANIFESTS/image_assets.jsonl` and `01_DIAGRAM_IMAGES/*.webp`. Start app using `--v4-root "$HOME/Desktop/14_MULTIMODAL_MEDIA_AND_GRAPH"` if auto-detection fails.

The 572 figure image files are not included in this code upgrade. A manifest without binaries does not make an illustration available offline. Pixel positions of callout numbers are not verified.

## Source and safety status

The workflow references two pages retrieved from a BMW AG TIS mirror on 2026-11-21:
- Steering symptom diagnostic SI page 7: https://workshop-manuals.com/bmw/3_series_e30/325ix_m20_sal/1_service_information/32__steering_and_wheel_alignment/2_si__aid_to_diagnosing_the_steering_system/page_92/
- Wheel-alignment precondition page 1: https://workshop-manuals.com/bmw/3_series_e30/325ix_m20_sal/2_repair_instructions/32__steering_and_wheel_alignment/0__electronic_chassis_alignment/1_ra__test_conditions_for_chassis_wheel_alignment_check/

These are **inspection guidance references only**; the service-information text is generic and the mirror's model index does not prove every later-system paragraph applies to this 1987-built Swiss iX. No original torque or defect tolerance, dismantling/pressing procedure, road-use clearance, or verified as-installed fitment is asserted.

## Release QA state

- The disposable installer/API/rollback suite requires an isolated V0.6-style baseline: `python3 test_rc070.py --baseline /path/to/disposable-baseline`. It must contain `app.py`, `sources.json`, `data/325ix_assemblies.sqlite3`, and a disposable `workshop_jobs.sqlite3`; never pass the owner's live workshop folder. The test copies it into a temporary directory before installation.
- Latest sandbox run: **47 PASS / 0 FAIL** using a disposable legacy-schema fixture adapted from the read-only V4 catalog and a synthetic PNG. The overlay acceptance count is 85 exact-number source-provenance records, not VIN or fitment approval.
- A synthetic image route check does NOT prove the actual BMW V4 pack has been installed or rendered on the owner's Mac.
- Real 8-GB Intel Monterey browser, keyboard and image asset testing, qualified mechanic workflow review, and model-appropriate original BMW repair procedure remain P0 gates before workshop approval.
