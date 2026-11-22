#!/usr/bin/env python3
"""Convert the dated public maintenance intake into indexable text.

The original PDFs and HTML files remain untouched. This creates derived text
and provenance sidecars for the existing manual indexer; it does not assert
BMW authority, copyright clearance, or vehicle applicability.
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "missing_materials_20261122"
OUT = ROOT / "maintenance_web_gap_input"
STAMP = datetime.now(timezone.utc).isoformat(timespec="seconds")

URLS = {
    "SRC-WEB-ETM-1988-325iX.pdf": "https://www.armchair.mb.ca/~dave/BMW/e30/e30ix_88.pdf",
    "SRC-WEB-E30-ARCHIVE-ETM-1987.pdf": "https://www.e30archive.com/documents/e30_electrical_1987.pdf",
    "SRC-WEB-E30-OWNER-MANUAL-DE.pdf": "https://e30-talk.com/Betriebsanleitung-E30.pdf",
    "SRC-WEB-IX-UNDERLAGEN-DE.pdf": "https://www.e30.de/fotostory/f01890/325iX%20Unterlagen.pdf",
    "SRC-WEB-E30-ARCHIVE-DOCUMENTS.html": "https://www.e30archive.com/en/documents",
    "SRC-WEB-IX-FAQ.html": "https://www.325ix.com/ixregistry/iX/general/iXfaq.html",
    "SRC-WEB-IX-STEERING-SUSPENSION.html": "https://www.e30archive.com/en/technical/suspension",
    "SRC-WEB-IX-TRANSFER-CASE-REBUILD.html": "https://www.r3vlimited.com/board/forum/e30-technical-forums/325ix-technical-and-discussion/367708-325ix-transfer-case-rebuild-diy",
    "SRC-WEB-IX-VISCOUS-COUPLING-REBUILD.html": "https://www.r3vlimited.com/board/forum/e30-technical-forums/325ix-technical-and-discussion/367707-325ix-rebuild-able-viscous-coupling",
    "SRC-WEB-WORKSHOP-IX-FRONT-STEERING-INDEX.html": "https://workshop-manuals.com/bmw/3_series_e30/325ix_m20_sal/fullindex/chapter-176/",
    "SRC-WEB-WORKSHOP-IX-TORQUE-INDEX.html": "https://workshop-manuals.com/bmw/3_Series_E30/325ix_M20_SAL/fullindex/chapter-866/",
    "SRC-WEB-WORKSHOP-IX-FLUIDS-INDEX.html": "https://workshop-manuals.com/bmw/3_series_e30/325ix_m20_sal/fullindex/chapter-1188/",
    "SRC-WEB-WORKSHOP-IX-STEERING-DIAGNOSIS.html": "https://workshop-manuals.com/bmw/3_series_e30/325ix_m20_sal/1_service_information/32__steering_and_wheel_alignment/2_si__aid_to_diagnosing_the_steering_system/page_92/",
    "SRC-WEB-WORKSHOP-IX-ALIGNMENT-CONDITIONS.html": "https://workshop-manuals.com/bmw/3_series_e30/325ix_m20_sal/2_repair_instructions/32__steering_and_wheel_alignment/0__electronic_chassis_alignment/1_ra__test_conditions_for_chassis_wheel_alignment_check/",
    "SRC-WEB-SERVICE-BULLETINS-E30.html": "https://www.rtsauto.com/bmw-e30-service-bulletin-index-complete-list-by-system-group/",
    "SRC-WEB-AWD-OVERVIEW-CHARM.html": "https://charm.li/BMW/1987/325es%20%28E30%29%20L6-2693cc%202.7L%20SOHC%20%28M20%29/Repair%20and%20Diagnosis/Technical%20Service%20Bulletins/All%20Technical%20Service%20Bulletins/Drivetrain%20-%20All-Wheel%20Drive%20Description%2FSpecifications/Overview/",
    "SRC-WEB-IX-SPECIAL-TOOLS.html": "https://charm.li/BMW/1987/325e%20%28E30%29%20L6-2693cc%202.7L%20SOHC%20%28M20%29/Repair%20and%20Diagnosis/Technical%20Service%20Bulletins/All%20Technical%20Service%20Bulletins/Special%20Tools%20For%20the%20325IX%20%284-Wheel%20Drive%29/",
    "SRC-WEB-IX-FRONT-DIFF-LUBRICANT.html": "https://charm.li/BMW/1987/325es%20%28E30%29%20L6-2693cc%202.7L%20SOHC%20%28M20%29/Repair%20and%20Diagnosis/Technical%20Service%20Bulletins/All%20Technical%20Service%20Bulletins/Drivetrain%20-%20Front%20Axle%20Final%20Drive%20Lubricant/",
    "SRC-WEB-IX-TOWING-CAUTIONS.html": "https://charm.li/BMW/1987/325e%20%28E30%29%20L6-2693cc%202.7L%20SOHC%20%28M20%29/Repair%20and%20Diagnosis/Technical%20Service%20Bulletins/All%20Technical%20Service%20Bulletins/Towing%20and%20Wheel%20Balancing%20-%20All%20Wheel%20Drive%20Cautions/",
    "SRC-WEB-IX-TRANSFER-CASE-ATF.html": "https://charm.li/BMW/1987/325es%20%28E30%29%20L6-2693cc%202.7L%20SOHC%20%28M20%29/Repair%20and%20Diagnosis/Technical%20Service%20Bulletins/All%20Technical%20Service%20Bulletins/Transfer%20Case%20-%20Exchange%20Shipped%20With%20ATF%2FVents%20Closed/",
}

def classify(name: str):
    if name.endswith(".pdf"):
        kind = "PUBLIC_DOCUMENT_DOWNLOAD"
        dtype = "OWNER_MANUAL" if "OWNER" in name else "ELECTRICAL_MANUAL" if "ETM" in name else "PUBLIC_TECHNICAL_DOSSIER"
    else:
        kind = "PUBLIC_WEB_EXTRACT"
        dtype = "PUBLIC_WORKSHOP_OR_COMMUNITY_EXTRACT"
    exact = "1988 BMW E30 325iX Swiss ECE; verify VIN applicability and as-installed configuration"
    if "1987" in name or "1987" in URLS.get(name, ""):
        scope = "1987 E30 comparison or 325iX reference; not a substitute for the 1988 Swiss ECE vehicle"
    elif "325iX" in name or "IX-" in name or "WORKSHOP-IX" in name or "AWD" in name:
        scope = exact
    else:
        scope = "BMW E30 family; model/market applicability requires verification"
    return kind, dtype, scope

OUT.mkdir(parents=True, exist_ok=True)
created = []
for source_name, url in URLS.items():
    source = SOURCE / source_name
    if not source.is_file():
        continue
    target = OUT / (source.stem + ".txt")
    if source.suffix.lower() == ".pdf":
        subprocess.run(["pdftotext", "-layout", str(source), str(target)], check=True)
    else:
        subprocess.run(["pandoc", "-f", "html", "-t", "plain", "--wrap=none", str(source), "-o", str(target)], check=True)
    kind, dtype, scope = classify(source_name)
    meta = {
        "title": source_name,
        "source_url": url,
        "market": scope,
        "variant_scope": scope,
        "document_type": dtype,
        "source_kind": kind,
        "authority": "PUBLIC SOURCE; reuse rights unverified; applicability review required",
        "verification_status": "T2_PUBLIC_ACQUISITION; NOT_INDEPENDENTLY_AUTHENTICATED",
        "retrieved_utc": STAMP,
    }
    (OUT / (source.stem + ".metadata.json")).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    created.append({"source": source_name, "text": target.name, "metadata": meta})

(OUT / "manifest.json").write_text(json.dumps({
    "status": "READY_FOR_CONTROLLED_MANUAL_IMPORT",
    "retrieved_utc": STAMP,
    "documents": len(created),
    "records": created,
    "rights_policy": "Public accessibility does not prove reuse rights, OEM authority or VIN applicability.",
}, indent=2) + "\n", encoding="utf-8")
print(f"READY: {len(created)} web-gap documents normalized into {OUT}")
