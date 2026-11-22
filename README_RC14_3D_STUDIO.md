# RC14 — Real GLB 3D Studio source preview

Extends immutable RC13. Code integration exists and legacy end-to-end catalog/mission regression passes in isolation. The reference model and local MIT JavaScript modules are prepared by a one-time network installer; the model is **not bundled in this archive** and no complete 3D browser/device acceptance has yet been observed.

1. Extract this ZIP into a NEW directory; never overwrite earlier releases or your active workshop database.
2. Start `bash RUN_325IX_3D_STUDIO.command` (macOS double-click may require right-click → Open). Requires Python 3.10+. The launcher performs first-time dependency/model download, makes an isolated job DB, starts the local server and opens your browser.
3. Choose **Digital Twin**. If the E30 mesh is loaded, use mouse orbit/wheel zoom, explosion slider, camera presets and mesh picking. Select an iX system to inspect its indexed drawings, exact callouts, part dossier and mission links.
4. If 3D assets are not downloaded, use the 2D fallback without losing any catalog/work-order functions. Run `python3 scripts/prepare_3d_assets.py` again when network access is available, then restart.
5. Test `python3 release_check_rc14.py`; check `3D_RELEASE_STATUS.json` before calling anything production-ready.

The downloadable model is an **E30 M3 reference by Martin Trafas, CC BY 4.0**, not dimensional mechanical or body accuracy for the four-door AWD 325iX. Mesh picks are not part-number identities. See `docs/3D_ASSETS.md`.

**Known blockers:** Model retrieval and webGL on owner Mac not observed; four-door 325iX mesh not available at a verified reuse source; GitHub repository created; source publication and verification tracked separately. Safe operating status remains NOT_APPROVED.
