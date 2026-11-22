# BMW 325iX Restoration OS — RC13 Visual Twin Trial

RC13 extends the system-wide candidate with the first usable visual twin slice. It covers AWD/drivetrain, suspension/steering, brakes, engine support, transmission/clutch and electrical missions through one Garage and Living Mission journey, plus an interactive non-dimensional vehicle map and 2D catalog fallback with numbered callout hotspots. Front axle remains the proving case, not the product boundary.

## Safest test on Saleem's Mac

1. Stop the old Workbench with `Ctrl+C`.
2. Extract this RC12 ZIP to a new folder; do not overwrite the existing Workbench.
3. Double-click `RUN_RC12_TRIAL.command`. If macOS blocks it, open Terminal in the extracted folder and run `bash RUN_RC12_TRIAL.command`.
4. The launcher opens the correct RC12 page automatically. If port `8765` is occupied by the old Workbench, it selects the next free port and prints the exact address.

The launcher reads `~/Desktop/325ix_workbench/workshop_jobs.sqlite3` and creates a separate integrity-checked trial copy under `rc12_trial_state/`. The original job database is not modified. To use another source database, run:

```bash
bash RUN_RC12_TRIAL.command --source-jobs /exact/path/workshop_jobs.sqlite3
```

## Acceptance walk-through

- Garage shows all P0 mechanical/electrical domains.
- Start or resume an AWD or electrical mission.
- Living Mission shows the next evidence gate and blockers.
- Record an observation and a calibrated measurement with unit/method/source.
- Save a checkpoint and a repair-first option.
- Ask the contextual AI mechanic; optionally save its answer only as a review-required finding.
- Export the work order and confirm the original database remains unchanged.
- Open Digital Twin, click an iX system zone, open its 2D fallback, choose an assembly, then select a numbered callout to open its part dossier.

## Visual-twin boundary

The 3D view is an offline SVG/isometric orientation map designed for fast workshop navigation and old-device compatibility. It is not CAD, does not claim exact dimensions, and does not establish fitment. The 2D fallback reuses the indexed BMW diagrams and exact catalog rows; hotspot positions are numbered callout controls, not inferred pixel coordinates.

Safety clearance always remains `NOT_APPROVED` without qualified physical sign-off. Browser-device visual acceptance and owner feedback are the purpose of this candidate.
