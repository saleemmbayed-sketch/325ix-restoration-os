# Evidence and stream reconciliation

**Snapshot date:** 2026-11-23 UTC
**State:** Read-only reconciliation; not a release approval, fitment decision, repair instruction, or safety sign-off.

## Stream identity

The program-operations root currently lists **S1 Parts, S2 Manuals, S3 Photos, S4 Fitment, S5 Diagnostics, S6 Workbench QA, and C0 Coordinator**. Separately, the repository delivery plan and GitHub acceptance scope name **S7 Integration**. S7 run artifacts exist under the front-axle expert integration run archive, rather than as an S7 folder in the current program-operations stream root.

Therefore, **C0 is not treated as S7**. The application workflow contract lists `S7_INTEGRATION` and `C0_COORDINATOR` separately. That corrects the code label, but it does not provide the missing authoritative Drive-to-GitHub crosswalk. Issue #5 remains open until owners publish the mapping, accountable owner, evidence IDs/hashes, and acceptance status for every stream.

## Evidence reviewed

| Lane / run | What the inspected records establish | What remains open |
|---|---|---|
| **S1 — `RESEARCH_DELTA_20261123_1030.jsonl`** | Five secondary source-reviewed gearbox/selector records. Every record is explicitly `NOT_APPROVED`; the claims do not establish installed gearbox identity or interchangeability. | Independent applicability, source-page review, installed-part identity, and fitment approval. The older S7 triage below does not cover this newer delta. |
| **S2 — `S2_20261122_095613_AUTOMATION_TURN5_ETM_REGISTRY`** | `PARTIAL`; one source-metadata candidate; zero verified items and zero manual pages inspected. The 1988 325iX ETM is a listing candidate, not a verified procedure. | Authorized manual access and rights, actual page/revision inspection, and Swiss/ECE 1987-12 applicability. The front-axle procedure task remains open. |
| **S3 — `S3-20261122-0055-automation-multilane-003`** | `PARTIAL`; a capture-card template only; zero verified items, zero photos, and zero exact numbers verified. | Owner/workshop photos, visible markings, source linkage, and usage authorization. A template is not photo evidence. |
| **S4** | The reviewed date-boundary report supports a USA catalog split for a limited steering claim. | Its applicability to the Swiss/ECE 1987-12 vehicle and as-installed part remains unresolved. It is not VIN fitment approval. |
| **S5 / S6** | These payloads were not fully audited in this reconciliation. | Do not infer completion or acceptance from stream presence or an operations summary. |
| **S7 — `S7_REAL_S1_JSONL_TRIAGE_1048.zip`** | The included report compares an older 4-record baseline and 6-record candidate. It reports all six candidate rows quarantined for missing assembly/variant/source-page/fitment fields and `HOLD_NO_AUTO_MERGE`. | This is not a canonical snapshot, does not cover the Nov. 23 S1 delta, and is not an audit of all S1–S6 work. |
| **S7 — `S7_CANONICAL_SNAPSHOT_GATE_1145.zip`** | The included ledger reports eight synthetic gate tests passing and explicitly says no live dataset was processed. | S1 must provide a complete, revisioned canonical snapshot with source-batch IDs; then exceptions require manual adjudication. Synthetic tests do not verify source provenance. |
| **C0 — `C0_20261123_RC21_RENDER_INTEGRITY_01`** | `PARTIAL`, zero new verified items. The report defers real browser/device acceptance, complete user journeys, and semantic mapping/assembled pose for opaque M20 meshes. | Owner-device acceptance and the stated semantic/visual gates. A separate local handoff regression does not close those gates. |

## Package and safety interpretation

- The local test bundle uses a **separate, synthetic `DEMO-*` catalog** so the UI can run without private Drive data. It is not an evidence import and does not demonstrate full-catalog completeness.
- Catalog occurrences, reference geometry, source metadata, and installed-part identity remain distinct. No entry here approves fitment, repairs, road use, or safety.
- The two previously unreadable S2/S3 JSONL records were downloaded read-only and retained in the local ignored Drive mirror; no Drive source was edited.
- No RC13 archive was found in the searched local locations, so no runtime import was performed.

## Closure requirements

1. Publish an authoritative S1–S7/C0 crosswalk with definitions, owners, source paths, immutable evidence IDs/hashes, and acceptance criteria.
2. Complete the stream-specific evidence gaps above; do not equate a source candidate, template, or synthetic test with a verified item.
3. Keep Mac/device acceptance, geometry licensing/identity, fitment, and qualified safety sign-off as independent external gates.
