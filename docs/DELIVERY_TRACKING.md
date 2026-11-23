# Delivery tracking — S1–S7 and 3D Studio

Canonical detailed research workstreams, acceptance rules, release history and source registries remain in Google Drive: `325IX DATA` (private archive; link configured by owner). This document records code-integration responsibilities without copying those records.

**Stream naming:** S7 Integration is a distinct delivery lane; C0 Coordinator is a distinct Program Operations lane. Do not count C0 reports as S7 evidence. The current Program Operations root has S1–S6 and C0 folders; separate S7 run artifacts are archived under the front-axle expert integration tree. The authoritative crosswalk is still an open requirement; see [evidence reconciliation](EVIDENCE_RECONCILIATION.md).

| Lane | Outcome (end-to-end) | GitHub proof requirement |
|---|---|---|
| S1 Parts | 7,190 exact-number reviews; source conflicts preserved | Exact 11-digit number, URL/review date per record; only evidence delta imported |
| S2 Manuals | Repair, electrical and TIS page evidence with rights | Real page/variant identification; no copied restricted manual |
| S3 Photos | Permission-appropriate exact part photographs | Rights and view manifest; no unauthorized third-party binaries |
| S4 Fitment | Variant/left-right/production-date/conflict assessment | Source + dimensions/physical verification; never automatic fitment clearance |
| S5 Diagnostics | Symptom → checks → documented evidence → repair-first alternatives | Correct procedure, discriminating test, stop condition and no fabricated torque |
| S6 Workbench QA | Portable local workshop UI + recoverable jobs | Regression against isolated copy, no owner-DB edits, safe rollbacks |
| S7 Integration | Cross-domain product and release coherence | Single shared contracts; all gates evidence-backed; no false feature closure |
| C0 Coordinator | Program-operations coordination and integration reporting | Separate coordinator output; never substitutes for S7 evidence or acceptance |
| 3D Visual Studio | Real E30 reference mesh ↔ selectable iX system ↔ 2D catalog ↔ mission | Render/orbit/pick/explode, exact catalog drilldown, fallback, rights and device test |

## First product increment: 3D studio with real catalog reachability

**Implemented in RC14 source preview:** Three.js GLTF loader and model download pipeline, local server allowlist, mesh pick/explode/camera controls, iX system selector, 2D drawing fallback, catalog part dossier, restoration mission handoff; offline integration test harness. All preserved as an additive layer over the existing RC13 implementation.

**Open acceptance gates:** Model and renderer files download successfully to owner computer; visual browser interaction on Mac Monterey; UI quality on actual hardware; mesh names and 3D component group semantics (reference only); four-door sedan licensing and geometry adoption if available; deployment to new public GitHub repo; workshop-device validation and physical sign-offs.

Do not silently convert open gates to passed, and never mark roadworthiness from AI output, catalog presence, reference meshes, or gamification.
