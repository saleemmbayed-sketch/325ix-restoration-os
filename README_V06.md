# BMW 325iX Workbench 0.6 — Catalog Completion Program

## Purpose
The 805 exploded assemblies, 13,845 catalog records and 572 unique drawing assets are complete as indexed source material. **This does not imply 7,190 exact-part photo and specification dossiers are complete.**

0.6 adds a full-catalog research tab for every unique BMW part number, prioritized in 144 batches of 50, and a separate source-reviewed overlay for 19 researched numbers. Original ETK rows and work orders are never rewritten.

## Install (Intel Mac, Monterey 12.7)
Stop the running Workbench with Ctrl+C. Extract the ZIP folder `325ix_upgrade_v06` on Desktop, then run:

```bash
bash "$HOME/Desktop/325ix_upgrade_v06/install_upgrade.sh"
cd "$HOME/Desktop/325ix_workbench"
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 app.py
```

The installer requires Python >=3.10; it detects 3.11 and preserves jobs, catalogs, local product photos, manual indexes and V4 images. Do not use sudo. This release may be installed on top of any existing 0.1-0.5 workbench that has the original 805-assembly database.

Open http://127.0.0.1:8765 and choose **Full catalog progress**. Select batches and click **Open part dossier**. Research leads can be searched online, but they are **not evidence** until the exact matched part has been reviewed. Part dossiers show linked explosion drawings if your V4 root is connected.

For V4 diagrams, preserve the Drive folder structure on your Mac and start with `python3 app.py --v4-root "$HOME/Desktop/14_MULTIMODAL_MEDIA_AND_GRAPH"` if needed.

## Source and fitment safeguards
- 40 unique numbers have conflicting LEFT/RIGHT wording somewhere in their catalog appearances. Review these, not automatically correct them.
- 347 numbers have multiple catalog description strings; not all are errors.
- 505 numbers have multiple date-condition strings, making vintage applicability especially uncertain.
- Sourced supplier photos do NOT prove physical installation, and URLs are not local image files. Currently only 6 external photo references exist in the 19 researched records. There are 0 verified offline individual-product photographs.
- An ETK catalog is not a BMW workshop manual; no torque, dimensional equivalence, wiring, or roadworthiness approval should be inferred.

## Outputs & next batches
Full program lives alongside the workbench in `16_FULL_CATALOG_ENRICHMENT`: `CATALOG_ENRICHMENT_MASTER.csv`, master JSONL, 144 numbered batch worklists, `CURATED_EVIDENCE_V06.json`, `COVERAGE_AND_GAPS.json`, source-verification script and progress report.

Run `catalog_enrichment.py validate` before merging any new sourced JSONL. Do not overwrite existing curated evidence blindly. Each new record must contain at least one HTTPS evidence source, status, and individual source links for each photo/fact. A validated source record is still NOT the same as owner-measured fitment or certified specs.
