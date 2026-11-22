# RC19 · Interactive Mechanic — three checkpoints

**Delivery:** an interactive mechanical layer in the existing BMW 325iX Restoration OS. No new frontend framework or external runtime dependencies beyond the Three.js kit already used by RC18.

## Three working journeys

1. **Open bonnet / enter assembly.** In **Explore vehicle**, choose **Open bonnet**, **Front axle**, or **AWD driveline**. The original GLBs ship inside this release; the M20 bonnet uses a front-edge hinge animation. Orbit/zoom/select, explode, isolate, and reset are in the existing Three.js viewer. The interface also lists the selectable components if mesh picking is inconvenient.
2. **Select component / inspect BMW evidence.** Pick a modeled component or its name; the workbench searches the original 805-assembly catalog for candidate OEM records. Select a specific occurrence to preserve its part number and parent assembly. Switch to real original BMW drawings or the full parts dossier. Visual geometry never asserts VIN-specific part identity, dimensions, torque or verified fitment.
3. **Record and resume actual repair.** Record the real symptom and optionally a source-attributed observation. The backend writes an isolated SQLite inspection job, its BMW assembly candidate and observation, then opens the persisted eight-stage restoration mission. Existing repair-first options, AI mechanic, evidence and safety sign-off rules remain unchanged.

## Included original geometry

| Scene | Unique selectable components | GLB mesh segments | Source |
|---|---:|---:|---|
| M20 inline-six engine bay with bonnet | 32 | 102 | Built specifically for this interactive personal reference |
| 325iX-inspired front axle/struts/steering | 14 | 27 | Built specifically for this reference |
| AWD transfer case and driveline | 11 | 19 | Built specifically for this reference |

The original geometry is a *stylized orientation model*, not a BMW factory CAD file or dimensional scan. Detailed OEM parts and production variants remain sourced from the existing catalog and inspected manuals. Any user-supplied licensed scan can replace an assembly via the existing private model library; nothing from that library goes to GitHub.

## Launch on an Intel Mac

Extract into a new directory; **do not overwrite your old working copy or job database**. Run `bash RUN_325IX_3D_STUDIO.command` in Terminal. For locally interactive WebGL, Three.js must be installed. The fully self-contained release bundles the pinned renderer where available; otherwise `bash INSTALL_3D_ASSETS.command` installs the existing verified free kit. The model itself ships locally so no third-party model download is needed. The same component-to-OEM-to-job workflow remains available with offline 2D previews.

## Verified acceptance

- Local browser with real catalog API: component selection → 49 matching M20 intake entries, selection of an OEM occurrence → persisted inspection and source-attributed observation → mission reopen. Front strut keyword fallback gave 16 real catalog matches. Front axle and AWD navigation passed with no page errors.
- Existing regression tests (`test_mvp_integration.py`, `test_rc17_models.py`, `test_rc18_ux_contract.py`, `test_viewer3d_contract.py`, `test_rc12_launcher.py`) pass against isolated copies.
- `test_rc19_mechanical.py` verifies all three GLBs, hashes and semantic meshes without requiring Blender or paid software.
- The additional GitHub browser acceptance test renders the three GLBs in Chromium/WebGL and exercises bonnet, component semantic focus/isolation and reset; owner Mac remains the device acceptance target.

**No AI diagnosis, rendered component, game progress or selection grants road-use approval.**
