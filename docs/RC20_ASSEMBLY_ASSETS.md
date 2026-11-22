# RC20 — BMW E30 exploded-view assembly asset sourcing (2026-11-22)

## Purpose and accuracy boundary
Existing linked OEM parts records and verified physical inspection remain authoritative. A scene mesh can be detailed and useful without being measured 325iX factory CAD. No unsupported dimensions, part numbers, fastening specifications, or verified fitment are inferred from a model. Redistribution requires the author/model license, even for personal-use-only sources.

## Ranked source candidates

| Priority | Assembly / source | Format and separation evidence | License / access | Decision |
|---|---|---|---|---|
| 1 | E30 1986 (FL, LP) by Krzysztof Stolorz, https://sketchfab.com/KrStolorz ; https://krsto.artstation.com/projects/Oy5596 | Free downloadable E30 model; author shows rig, opened panels; actual Blender/GLB hierarchy must be inspected | Free advertised, specific rights check on download | Best replacement for coarse exterior and bonnet/door pivots |
| 1 | Engine Inspired by M20 Engine (GrabCAD; indexed at https://www.stlfinder.com/3dmodels/bmw-m20-engine/) | Search listing says full assembly of major engine components | Original download not verified, account may be needed | First authentic-looking component-separated M20 candidate to request |
| 1 | BMW M20 engine animation (Creo + KeyShot), https://www.youtube.com/watch?v=Whv7-XE6EpU | Creo CAD used for the animation, no linked CAD file verified | Video may be viewed but source CAD distribution unverified | Mechanical appearance reference only; could request source from author |
| 2 | E30 325iX spindle / front differential collection, https://sketchfab.com/OsamaMaddani/collections/bmw-e30-5eea3c5286de4c58b7de7c2eb48597a5 | iX-specific component models; exact downloadable file & grouping unverified | Check model-level download permission | Improve iX front axle and AWD specificity when downloaded |
| 2 | Generic exploded engine (https://sketchfab.com/3d-models/engine-exploded-view-0a740cd20bfd4107a1e3c9fbcc5fe70b) | Explicit download-model listing, exploded style | License and source format to inspect | Reference for interaction style, NOT M20 geometry |
| 2 | Free car differential 34 individual STL parts + GLB (https://engx3d.com/3d-models/car-differential) | Site advertises named GLB and 34 separate STL files | Check model page download terms; site request currently blocked in local environment | Test isolation, component identity, explode, import pipeline; never label as 325iX |
| 3 | E30 STEP pieces, https://automeshclub.com/parts | Free E30 rear differential bushings, rear subframe/control arm pieces | Local download, per-file provenance | Build accurate part-specific inserts after source checks |
| 3 | E30 original parts diagrams https://bmwfans.info/parts-catalog/E30-4-doors/Europe/325ix-M20/dec1987/browse/front_axle | 2D OEM component and positional references, not 3D CAD | External catalog, citation/reference only | Anchor part naming and callout evidence |
| 3 | 325iX transfer-case parts https://www.realoem.com/bmw/enUS/showparts?diagId=27_0001&id=1501-EUR---E30-BMW-325ix | True iX exploded parts illustrations | External catalog, citation/reference only | Anchor transfer-case identity and details |

## Policy for assembly imports
- Source each asset from its creator/authorized provider. Preserve original credit, source URL, source file checksum, rights, engine/vehicle variant and import date.
- Use the existing `scripts/prepare_vehicle_blender.py` to convert GLB, glTF, FBX and USD to hierarchical GLB. Never split by disconnected islands unless explicitly requested (`--split-loose`).
- Each top-level group is `Assembly:<role>` and component is `Component:<id>`; original mesh transforms remain in the assembled scene. Offsets are generated at runtime using one normalized `explodeFactor`, not baked keyframes.
- Free personal models may be stored on the user's Mac in private local model slots; do **not** copy to the public GitHub repo without redistributable rights.
- A 3D file is not presumed applicable to the original 1987-12 Swiss/ECE 325iX, or the installed replacement engine, without variant/source evidence.
