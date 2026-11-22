# RC16 · Ponytail visual workshop

The RC16 view uses the existing Three.js GLB runtime, 21 catalog system hotspots and searchable original BMW exploded drawings. The reference model is an **E30 M3**, not exact 325iX geometry. New features require no extra frontend dependencies.

**Local test:** extract into a new folder; run `RUN_325IX_3D_STUDIO.command`. It starts an isolated workshop trial. The launcher attempts to fetch the pinned, redistributable GLB runtime kit. If the model download is blocked, download [`325ix_3d_assets_v1.zip`](https://github.com/saleemmbayed-sketch/325ix-restoration-os/releases/tag/rc15-3d-runtime), then run `INSTALL_3D_ASSETS.command`. The OEM 2D diagrams remain usable without a GLB.

**Verification:** `python3 test_viewer3d_contract.py`, `python3 test_mvp_integration.py`, `python3 test_rc12_launcher.py`; see `docs/RC16_ACCEPTANCE.md` for measured before/after and remaining physical acceptance gates.
