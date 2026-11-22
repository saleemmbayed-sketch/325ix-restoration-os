# RC20 — Parametric exploded 3D E30 assembly studio

Uses the existing Three.js runtime and Python/SQLite catalog without introducing another app/framework. `explosion-rig.js` creates `Assembly:*` and `Component:*` pivots, preserves transforms at `explodeFactor=0`, and LERPs deterministic local positions for assemblies and components to any fraction in `[0, 1]`. Select a target group or component, isolate it, reset to assembled, or use the demonstrator telemetry button (explicitly a demo, not live vehicle data).

Public browser API (available only when the local model is loaded):

```js
ixTwinAPI.setExplodeFactor(0.65, { scope: 'Engine_Assembly', isolate: true });
ixTwinAPI.isolateAssembly('Cooling', true);
ixTwinAPI.getAssemblyTree();
ixTwinAPI.getTwinState();
ixTwinAPI.subscribe(state => console.log('Viewer state changed', state));
ixTwinAPI.triggerTelemetryAlert({ system: 'Cooling', metric: 'coolant_temp_c', value: 108, source: 'DEMO_ONLY' });
ixTwinAPI.reset();
```

Demo values are never real diagnostics. Exact part identity and safety still require the existing OEM dossier.

## Prep a licensed high-detail model (optional, free Blender)

```bash
blender -b --python scripts/prepare_vehicle_blender.py -- --input /path/to/source.fbx --output models/e30_prepared.glb
```

For a fused mesh use `--split-loose` only when it genuinely contains disconnected parts. Pass a JSON `--mapping assembly_map.json` when source names are insufficient. Pivot placement uses geometric centroids, not known material-density mass properties. See `docs/RC20_ASSEMBLY_ASSETS.md` for free candidates and source access.

## Acceptance caveat
Core rig geometry has a runnable automated Three.js test; fresh high-detail source import and end-user Mac device rendering remain physical acceptance gates. This release does **not** claim complete factory-grade 325iX mechanical CAD.
