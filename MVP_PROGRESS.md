# BMW 325iX Restoration OS — MVP Progress

Updated: 2026-11-22

## Product-owner release verdict

**MVP-0.9.0 RC13 is the system-wide visual-twin device-acceptance candidate.** The software integration is reproducible across the shared Garage, backend-derived Living Mission progress, embedded evidence/check/repair/AI workflows, guarded database recovery, and the new interactive non-dimensional vehicle map with 2D catalog fallback and numbered callout hotspots. Front axle remains the proving case while all priority 325iX mechanical/electrical domains share the same mission contract. It is **not workshop-approved and not safety-cleared** until the physical, source-verification, browser-device and human sign-off gates below are completed.

Release gate result: automated integration checks pass; safety clearance remains `NOT_APPROVED`.

## Audit verdict

The authoritative Drive workspace exists and is populated:

- V3 immutable corpus, V4 multimodal folder, V15 enrichment outputs, six-stream operations, Workbench pilot, and RC070 front-axle integration are present.
- S1 remains owned by its existing catalog-enrichment automation.
- S2–S6 remain represented in the existing interleaved worker and stream folders.
- RC070 is an internal test candidate, not workshop-approved. Its own gate blocks owner-installed photos, physical mechanic sign-off, visual acceptance, and live Arabic voice validation; this package closes the real V4 index/diagram integration gap for three release-critical assets.

## Implemented in this workspace

- Reused RC070 Workbench code and front-axle evidence workflow.
- Added an explicit specialist registry for identity, diagnostics, repair/rebuild, AWD fitment, sourcing and QA.
- Added `/api/specialists`, `/api/workflow/front-axle`, and `/api/integration/health`.
- Connected the real V4-derived multimodal SQLite index: 805 assemblies, 13,845 part occurrences, 572 image assets, 805 figure occurrences and 13,845 part-to-figure links.
- Materialized three read-only front-axle/steering diagrams from the existing V4 manifest; the original manifest remains untouched.
- Preserved the 7,190-record research registry as a read-only input and exposed its count in health checks.
- Added six connected specialist roles and a seven-stage front-axle workflow.
- Added grounded offline AI fallback: catalog identity and evidence-gap answers work without Ollama; it cannot diagnose, approve fitment or clear safety-critical work.
- Added a page-level manual evidence seam: authorized text can be indexed with document/page hashes, variant scope, market, source kind, authority and verification status; citations are returned to the UI and AI retrieval.
- Acquired and normalized the existing Drive maintenance corpus plus a dated public-source gap intake into a bundled read-only index: 57 source documents and 1,562 page/section records, including the exact 1988 325iX ETM, owner/manual references, factory/TIS pointers, electrical references, AWD service information, community repair evidence and OES catalog extracts.
- Added reproducible web-gap normalization with source URLs, retrieval timestamp, document class, variant scope, authority caveat and derived text/page hashes; originals remain separate from the index.
- Added explicit curated-claim conflict handling: conflicting values are surfaced as `UNRESOLVED` and passed to AI context without automatic selection.
- Added a persistent repair/sourcing comparison ledger on each case, ordered repair-existing → used/refurbished OEM → specification-verified cross-fit → new replacement; options require evidence and provenance and can only remain proposed, selected-pending-signoff or rejected.
- Added persistent evidence observations with type, value, unit, tool and source; case reopen, export and restart recovery are verified.
- Added release-health and reproducible integration checks.
- Added a workshop launchpad with live subsystem readiness, evidence-count visibility and explicit `NOT_APPROVED` safety state so a user knows what to do first.
- Added explicit English/Arabic AI output selection, RTL interface direction, optional browser dictation/read-aloud, and graceful text-only fallback when browser speech is unavailable.
- Added the first connected digital-twin slice: factory state, as-installed state and confidence are separate; structured events are persisted in the existing jobs database; case, observation and repair-option actions emit twin events; the UI exposes evidence history and evidence-only XP/level progress.
- Added a unified case overview contract and cockpit: job, checkpoints, observations, repair options, specialist steps and twin events are returned together with evidence count and current blockers; the safety gate remains explicit.
- Added specialist intent routing for the AI layer: requests are classified into identity, diagnostics, repair/rebuild, AWD fitment, sourcing or QA with required evidence, approval gate and safety class; the route is returned with grounded AI responses and shown in the UI.
- Added component-instance registry and uncertainty map: component location, side, marking, condition and facts persist separately; owner-reported, source-verified, mechanic-verified and conflicting states remain distinguishable and emit twin events.
- Added a system-wide restoration domain model for AWD/drivetrain, suspension/steering, brakes, engine/cooling/fuel/exhaust, transmission/clutch and electrical/controls; climate/visibility is P1, while body/trim/accessories remain searchable but deferred.
- Added the Garage home experience and persistent restoration missions. Generic jobs and the front-axle pilot now enter the same mission ledger, and missions survive restart.
- Added architecture governance in `PRODUCT_BLUEPRINT.md` and ADR 0001 so the front-axle proving case cannot silently become the product boundary again.
- Added the first Living Mission workspace: every P0 mission opens with an eight-stage evidence journey, explicit next gate, blockers, connected evidence totals and contextual routes into parts, technical evidence, AI, work orders and the digital twin.
- Added schema version 2, automatic integrity-checked pre-migration snapshots and a guarded rollback utility that refuses an active WAL and preserves the current database before restoring a selected backup.
- Embedded evidence capture, system-specific checkpoints, repair-first comparison and case-grounded AI directly in Living Mission. Model output can only be stored as a review-required specialist finding.
- Added an RC12 trial launcher that clones the owner's existing job database into isolated trial state before startup; the source database remains untouched.
- Fixed observed Mac launch failure when port 8765 is occupied: the launcher now selects the next free port, opens the exact RC12 address and shuts its child server down with the launcher.
- Added the first visual-twin delivery slice: an offline SVG/isometric vehicle orientation map covering the priority iX mechanical/electrical systems, clickable system zones, system-aware assembly lookup, 2D diagram fallback, numbered callout hotspot rail and linked part dossier. It intentionally makes no dimensional/CAD or fitment claim.

## Acceptance matrix

| Area | State | Evidence |
|---|---|---|
| P0 asset audit | PASS | Drive folders and control artifacts resolved; latest RC070 gate read |
| P1 shared integration seam | PASS (local derived release) | Health endpoint, specialist registry, workflow contract, real multimodal DB and preserved immutable inputs |
| P2 grounded local AI | PASS (offline controlled mode) | Retrieval-linked fallback and page-provenance manual excerpts work without an LLM; Ollama remains optional and separately gated |
| P3 front-axle Workbench | PASS (real catalog) | Search → exact part dossier → diagram → case → checkpoints → evidence → reopen → export |
| V4 real diagrams | PASS (3 release-critical assets) | Three existing front-axle assets materialized read-only; remaining 569 remain manifest-only |
| Manual RAG | PARTIAL / READY FOR CONTROLLED IMPORT | 57-document / 1,562-section index, metadata contract, page hashes, citations and search/API integration pass; source authority and model-specific repair approval remain unverified |
| Manual conflict handling | PASS (controlled claims) | Conflicts are exposed through `/api/manuals/conflicts` and never silently merged |
| Repair intelligence | PASS (ledger and policy gate) | Options persist, sort by repair-first policy, export with the work order and reject software approval states |
| Digital twin foundation | PASS (internal) | `/api/twin`, `/api/twin/event`, structured event validation, XP policy, UI rendering and restart persistence |
| Unified case cockpit | PASS (internal) | `/api/job/{id}/overview`, UI blocker summary and integration coverage |
| Specialist intent routing | PASS (internal) | `/api/ai/route`, routed grounded assistant response, UI route panel and integration coverage |
| Component registry and uncertainty | PASS (internal) | `/api/twin/components`, component/fact writes, uncertainty counts, UI registry and integration coverage |
| System-wide Garage and missions | PASS (internal contract) | Domain inventory covers every P0 system; AWD and electrical mission creation, listing and restart persistence pass alongside the suspension/steering proving case |
| Living Mission workspace | PASS (internal slice) | Shared UI consumes the case overview for any mission domain and keeps job context across evidence, part, AI, manual, export and twin actions |
| Interactive visual twin | PASS (internal candidate) | `/api/visual/twin`, clickable non-dimensional system map, catalog-backed 2D fallback, callout rail and part-dossier handoff; browser-device review still required |
| Database migration and rollback | PASS (controlled fixture) | Legacy row survives v0→v2 migration; pre-migration backup passes integrity check; guarded restore preserves current DB and restores selected snapshot |
| Physical fitment / measurements | HUMAN REQUIRED | Software cannot infer dimensions or sign off safety-critical work |
| S1–S6 live automation | PRESERVED / NOT RE-CERTIFIED | Existing schedules and outputs are preserved; no unsaved work counted as complete |

## Remaining release gates

1. Import authorized, model-appropriate BMW repair text using the new metadata contract; keep URL-only pointers visibly separate.
2. Add owner-installed component photos and calibrated physical measurements; require qualified inspection for steering, suspension, brakes, lifting and AWD interfaces.
3. Run browser UX and image rendering review on the workshop device, including Arabic text/voice if enabled.
4. Re-certify S2–S6 automation outputs from saved run reports and run the now-tested backup/rollback flow against a copy of the owner's operational workspace.
5. Add repair-versus-source comparison records and explicit contradiction/conflict resolution before any consequential recommendation.
6. Obtain qualified mechanic review and independent sign-off before changing clearance from `NOT_APPROVED`.
7. Complete browser-device visual review; the static UX source audit passed, but this environment could not launch Chromium for screenshot capture.

## Current milestone decision

RC13 is the first packaged visual candidate after RC12 because it adds a usable visual entry point without introducing CAD, model or orchestration complexity. It is released for observed device acceptance, not workshop or safety approval.

## Reproducible commands

```bash
python3 release_check.py
python3 test_mvp_integration.py
python3 app.py
```

The app automatically uses `04_SEARCH/325ix_multimodal.sqlite3` and the derived `03_MANIFESTS/image_assets_local.jsonl` when present. Mutable job/photo databases are deliberately not part of the release archive.

## RC21 verification checkpoint — 2026-11-24

- PR #6 now contains the isolated synthetic demo and read-only V4 full trial launchers, local 3D engine/axle/AWD models, inline candidate evidence, and a rendered Chromium journey in CI. The RC21 and source/3D workflows passed at commit `792ee0b`; the browser journey rendered the front-axle GLB, selected DEMO-STEER-001, saved case IX-0001, reopened its dossier, reloaded and restored selection, while clearance stayed `NOT_APPROVED`.
- Follow-up source-gap and review-context panel changes passed both GitHub workflows at commit `c6f490b`, including the rendered Chromium journey. Synthetic rows have no OEM citation; the panel must state that explicitly. A passing synthetic demo does not validate the owner's V4 diagram files, installed fitment, manual authority, Arabic voice, or macOS WebGL.
- The full V4 launcher checks the 805-assembly/13,845-occurrence catalog and clones the job DB into trial state. The local mirror used for a rehearsal lacked verified images and had inconsistent metadata; the owner's Mac/Drive copy still needs its own read-only health result.
- Release decision: RC21 remains a trial, not an accepted restoration release. Next gates are the owner's actual V4 health/diagram rendering, device browser inspection of all priority iX journeys, sourced maintenance procedures and qualified physical sign-off. Existing S1 enrichment ownership and S2–S6 rotation remain unchanged.

### RC21 visual review follow-up

- CI now saves three rendered Chromium screenshots (garage, selected component, saved case) as a seven-day artifact. Review of the first capture found a compressed 3D stage, a long blank grid column and raw JSON in narrow twin cells. The revised capture at commit `32a86b6` shows a full-width 3D stage, a separate broad inspection panel and labeled twin facts; the Chromium journey and both workflows passed.
- The visual remains an illustrative mechanical model with three authored assembly scenes, not a photorealistic whole-car CAD twin. The saved case workflow is still dense and the synthetic dataset cannot demonstrate production evidence coverage. A follow-up copy change is under verification to prevent owner-reported factory-profile fields being presented as source-verified factory records.

### RC21 full V4 trial guard

- The available copied V4 catalog passes SQLite integrity and contains 805 assemblies / 13,845 rows, but its image manifest reports `MISMATCH` and 0/572 locally verified files. This does not establish the state of the owner's Mac/Drive copy. The launcher reports the degraded state without modifying V4.
- The full trial launcher now stops if the original job DB path is absent and no existing trial DB is present; `--source-jobs` locates an alternate original, while `--fresh-trial` explicitly permits an empty start. A local fixture verified the missing-source guard, explicit empty opt-in, source copy and existing-trial reuse.

### Digital twin accuracy gate

- Fixed cumulative XP to sum the full persisted event ledger; the activity feed remains the latest 100. Creating an unverified component instance now records `COMPONENT_INSTANCE_CREATED` with zero identification credit, while historical events are preserved.
- The 3D component panel now opens the physical component intake with a locator label. It deliberately leaves OEM number, observed marking, condition and source empty. Browser and API regressions test that a visual candidate is never silently promoted to installed identity and that XP remains correct beyond 100 events.
- Still open: actual VIN and installed-component evidence on the owner's device, verified V4 image reconciliation, manual applicability, complete system coverage and qualified physical sign-off. The illustrated model is not yet an accurate as-built representation.
