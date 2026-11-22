# 3D assets, provenance and safety boundaries

## Sources and permitted use

- **Model:** BMW M3 E30 (1986–1991) reference mesh, by **Martin Trafas (`TinoD2`)**. Original Sketchfab model: https://sketchfab.com/3d-models/free-bmw-m3-e30-ac3c7013434e403e8faff87948caf422 . License documented by the original project as **Creative Commons Attribution 4.0 (CC BY 4.0)**: https://creativecommons.org/licenses/by/4.0/ . Must retain author credit and license notice.
- **Optimized GLB delivery:** https://github.com/ahnuchen/auto-atlas/blob/master/public/models/free_bmw_m3_e30.glb . Pinned Git blob SHA: `8aaa3daafd53158b63ced92c4c65d520ebce561f`. Optimized mesh is approximately 2.98 MB. Model use requires source/license review; no claims of exact four-door 325iX dimensions or component match.
- **Upstream exploded-view product:** https://github.com/ahnuchen/auto-atlas . **No explicit source-code license was found in the inspected repository root**. This product is referenced for the model and feature inspiration; no Auto Atlas application source is redistributed here.
- **Renderer:** Three.js version `0.159.0`, MIT. Source https://github.com/mrdoob/three.js ; downloaded files include Three.js LICENSE.
- **Decoder:** meshoptimizer version `0.22.0`, MIT, source https://github.com/zeux/meshoptimizer . Downloaded LICENSE retained locally.

## Download/install

Run `python3 scripts/prepare_3d_assets.py` while online. It downloads only the specific files listed in the script, verifies the original GLB using Git's exact blob hash, and writes the local SHA-256 report `models/asset-install-report.json`. The optimized model is **not** included in the source package because the model needs explicit attribution and provenance; this also avoids duplicating third-party assets in version control. Assets are cached locally afterward for offline use.

To use a legally acquired four-door E30 model instead, select **Load another licensed GLB** in the UI. The source and geometry need separate verification before distributing that asset or mapping its mesh names.

## Non-authoritative model

The E30 M3 model may differ substantially from the Swiss ECE LHD four-door AWD 325iX: fenders, bumpers, body style and AWD mechanical architecture. It is an interactive **visual reference**, not a verified component model, not a source for measured tolerances, torque or repair approval. Semantic system selection opens the authoritative 2D BMW catalog/evidence pipeline. Mesh picks are not mapped to OEM numbers without explicit verified mapping. Explosion offsets are illustrative, not disassembly directions.
