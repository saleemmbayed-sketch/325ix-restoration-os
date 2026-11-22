# BMW 325iX Restoration OS — Product Blueprint

Updated: 2026-11-22  
Vehicle: VIN `VIN_NOT_CONFIGURED` · 1987-12 Swiss ECE · LHD · manual AWD · installed M20B25 owner-confirmed

## Product promise

One local-first, evidence-grounded restoration workspace for the complete priority mechanical and electrical 325iX. The user sees one vehicle, one active mission, one AI mechanic and one evolving digital twin. Front axle is the first proven mission template, not the product boundary.

## Priority scope

| Domain | Priority | Catalog systems |
|---|---|---|
| AWD & Drivetrain | P0 | transfer box, propshaft/drive shaft |
| Suspension & Steering | P0 | front axle, rear axle, steering, wheels |
| Brakes | P0 | brakes and related inspection evidence |
| Engine, Cooling & Fuel | P0 | engine, radiator, fuel preparation/supply, exhaust |
| Transmission & Clutch | P0 | manual transmission, clutch, gearshift, pedals |
| Electrical & Controls | P0 | vehicle electrical, engine electrical, lighting, instruments |
| Climate & Visibility | P1 | heating, ventilation and demisting |

Bodywork, trim, seats, accessories, retrofits and entertainment remain searchable in the OEM catalog but are deferred from the default restoration journey. Deferral is not deletion.

## Product structure

| ID | Responsibility | Authoritative behavior |
|---|---|---|
| UX-01 | Garage and mission shell | Shows priority domains, active missions, blockers and next safe action |
| MS-01 | Restoration mission engine | Uses one job/evidence/checkpoint contract across all priority domains |
| TW-01 | Vehicle digital twin | Separates factory, catalog, owner-reported, source-verified, mechanic-verified and as-built truth |
| EV-01 | Evidence and RAG | Preserves source/page/hash/variant/rights/conflicts and case context |
| AI-01 | AI mechanic and specialists | Routes internally; returns evidence, uncertainty, tests and human handoff |
| WO-01 | Workshop execution and QA | Produces work orders, execution states, test results and qualified sign-off requests |
| GP-01 | Safe progress engine | Rewards evidence and completed QA; never changes fitment or safety clearance |
| OP-01 | Persistence and operations | Local-first recovery, external job DB, backups, migrations, monitoring and rollback |

## Central journey

Garage → choose/resume domain mission → report symptom/objective → identify component → collect photo/measurement → inspect catalog/diagram → retrieve applicable evidence → AI specialist reasoning → discriminating test → repair-first options → work order → execution/QA → qualified sign-off → digital-twin history and safe milestone.

## Delivery map

| Increment | Complete user promise | Acceptance boundary |
|---|---|---|
| M1 — System-wide Garage | Start and resume missions across every P0 domain using shared persistence and safety policy | Domain coverage, mission creation, restart recovery and deferred catalog scope verified |
| M2 — Living Mission | Complete one mission without navigating subsystem tabs | Evidence, checks, repair-first decisions and contextual AI are embedded; component photo capture, execution/QA and device acceptance remain |
| M3 — Visual Twin & Safe Quests | Understand restoration state and next evidence task visually | Unknown/observed/conflicting/verified/repaired zones and gated milestones are accessible and non-authoritative |
| M4 — Workshop Pilot | Use the product on the workshop device for a real case | Device UX, backups, rollback, owner photos/measurements and qualified QA sign-off verified |

Recovery contract: job database schema version 2 creates an integrity-checked snapshot before migration. Rollback is explicit, refuses an active WAL, verifies the selected backup and preserves the current database before replacement.

## Global invariants

1. No system is declared restored from catalog identity or AI output alone.
2. Factory configuration, catalog applicability and as-installed state never overwrite one another.
3. Every consequential claim links to evidence and explicit applicability.
4. Repair existing → used/refurbished OEM → verified cross-fit → new replacement.
5. V3/V4 remain immutable; mutable jobs/photos remain versioned and recoverable.
6. Body and trim cannot consume priority capacity while a P0 mission is incomplete unless the owner changes priority.
7. XP, quests and milestones cannot grant safety, fitment or road-use approval.

## Current evidence and open gates

Observed working before this blueprint: full catalog identity, multimodal graph, manual index, persistent jobs/evidence, front-axle pilot, digital-twin events/components, specialist routing, repair options and restart integration tests. System-wide Garage and mission behavior require fresh post-change verification. Visual workshop-device acceptance, schema migration/backup, qualified physical inspection and safety sign-off remain open.

