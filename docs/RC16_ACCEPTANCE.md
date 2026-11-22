# RC16 · Ponytail acceptance evidence

## Scope
- Keep the existing Python HTTP/SQLite application and Three.js renderer; **no new framework or dependency**.
- Remove the unused 21-node hand-drawn SVG map. Use a real GLB for non-dimensional orientation and *actual cached* OEM diagrams for numbered parts.
- Route 3D zone selection and text search through the same authoritative 21-system catalog/mission API.

## Measured against RC15
| Check | RC15 | RC16 | Evidence |
|---|---|---|---|
| Front axle auto-open, group and successive diagram requests | 1 group + 3 assembly requests | 1 group + 1 assembly request | Live API/browser test with cached drawing manifest |
| Engine auto-open, when no local diagram is cached | 1 group + up to 30 attempted assembly requests | 1 group + 1 assembly request | Availability flag from grouped query; no blind image search |
| Visible searchable whole-vehicle system list | Dropdown only (no search) | 21 indexed and searchable systems | Browser interaction test |
| 3D overlay selectable system markers | No marker layer | 21 approximate zones grouped into 4 regions | Renderer contract; real WebGL CI still required |
| OEM drawing fallback | Original diagram with assembly list | Same source drawing, fewer fetches and searchable assemblies | Live cached front-axle example; 24 part callouts |
| GPU pixel cap on high-DPI displays | 2x | 1.5x | Three.js renderer code; performance not measured on Mac |

**Important limitations:** The supplied reference GLB is a licensed BMW M3 E30, not a 4-door 325iX or 3D mechanical model. The reference still has **26 GLB meshes**, no exact iX front axle, transfer case or engine mechanical CAD. Approximate hotspots do not imply OEM part/mesh identity. Only three catalog figures are cached in the RC15/RC16 preview; 572 figures are indexed in the corpus. A real-device study is necessary to substantiate any claim about doubling visual fidelity, usability and time-on-task; the 100% improvement threshold has **not** been proven across all dimensions.

## Non-negotiable release gates
1. Real Mac Monterey browser acceptance: GLB rendered; orbit/zoom/mesh pick/region focus/part navigation/2D switching without errors and tolerable frame rate.
2. Full licensed 325iX-aware assembly geometry or explicit real 2D fallback for every indexed assembly; rights and source fingerprints logged.
3. No person-specific vehicle VIN, owner assets, workshop jobs, private Drive references or restricted drawings shipped to public GitHub.
4. Existing catalog, missions, evidence, repair-first workflow and safety sign-off behavior unchanged and regression tested.
