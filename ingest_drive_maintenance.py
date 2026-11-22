#!/usr/bin/env python3
"""Normalize the existing Drive maintenance corpus into the Workbench manual index.

This consumes only already acquired local extracts. It does not scrape the web,
alter the authoritative Drive corpus, or upgrade public/community material into
BMW-authorized procedures. Source tier, variant scope and rights caveats remain
part of each document's metadata.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path


def source_id_from(path):
    match = re.match(r"(SRC-\d+)", path.name)
    return match.group(1) if match else path.stem


def metadata_for(corpus, source_id, records):
    sidecar = next(corpus.rglob(source_id + '_metadata.json'), None)
    meta = {}
    if sidecar:
        try:
            raw = json.loads(sidecar.read_text(encoding='utf-8'))
            meta = raw.get('manifest_record', {}) if isinstance(raw, dict) else {}
            archive = raw.get('archive', {}) if isinstance(raw, dict) else {}
        except (OSError, json.JSONDecodeError):
            archive = {}
    else:
        archive = {}
    first = records[0]
    source_class = str(first.get('source_class') or meta.get('access_class') or 'PUBLIC_EXTRACT')
    tier = str(meta.get('evidence_tier') or 'T3')
    target = str(meta.get('target_body') or 'EU E30 325iX; exact variant requires verification')
    applicability = str(meta.get('applicability_note') or 'Verify production date, market, body and installed configuration')
    rights = str(archive.get('rights_status') or meta.get('license_status') or 'publicly accessible; reuse rights unverified')
    authority = f"{meta.get('publisher') or 'PUBLIC SOURCE'}; {rights}"
    if source_class == 'official_public_pdf':
        document_type = 'PUBLIC_OES_CATALOG_OR_REFERENCE'
    elif source_class == 'public_catalog':
        document_type = 'PUBLIC_PARTS_CATALOG'
    else:
        document_type = 'PUBLIC_WORKSHOP_OR_COMMUNITY_EXTRACT'
    return {
        'title': str(meta.get('title') or first.get('file') or source_id)[:200],
        'source_url': str(meta.get('url') or first.get('source_url') or '')[:1000],
        'market': target[:100],
        'variant_scope': (target + '; ' + applicability)[:160],
        'document_type': document_type,
        'source_kind': source_class[:100],
        'authority': authority[:160],
        'verification_status': f'{tier}; EXTRACTED_TEXT; MODEL_APPLICABILITY_REVIEW_REQUIRED',
        'evidence_tier': tier,
        'rights_status': rights,
        'publisher': str(meta.get('publisher') or '')[:160],
        'source_id': source_id,
        'archive_sha256': str(archive.get('sha256') or '')[:64],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--output-input', type=Path, required=True)
    parser.add_argument('--output-index', type=Path, required=True)
    parser.add_argument('--output-manifest', type=Path, required=True)
    args = parser.parse_args()
    extracted = args.corpus / '09_EXTRACTED_TEXT'
    if not extracted.is_dir():
        parser.error('Missing 09_EXTRACTED_TEXT under corpus')
    args.output_input.mkdir(parents=True, exist_ok=True)
    manifest = []
    documents = 0
    page_sections = 0
    for path in sorted(extracted.glob('*.jsonl')):
        records = []
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and str(value.get('text') or '').strip():
                records.append(value)
        if not records:
            continue
        source_id = source_id_from(path)
        meta = metadata_for(args.corpus, source_id, records)
        text_parts = []
        for record in records:
            locator = record.get('page') or record.get('page_id') or record.get('chunk_id') or 'section'
            text_parts.append(f"SOURCE LOCATOR: {locator}\n{record['text'].strip()}")
        output = args.output_input / (source_id + '.txt')
        output.write_text('\f'.join(text_parts) + '\n', encoding='utf-8')
        sidecar = output.with_name(output.stem + '.metadata.json')
        sidecar.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        manifest.append({**meta, 'input_file': str(output.name), 'record_count': len(records),
                         'text_chars': sum(len(x['text']) for x in records)})
        documents += 1
        page_sections += len(records)
    args.output_manifest.write_text(json.dumps({
        'status': 'READY_FOR_CONTROLLED_MANUAL_IMPORT',
        'documents': documents,
        'page_sections': page_sections,
        'rights_policy': 'Offline private-study archive; publicly accessible does not prove reuse rights or OEM authority.',
        'records': manifest,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    command = ['python3', str(Path(__file__).with_name('index_manuals.py')), '--input', str(args.output_input), '--output', str(args.output_index)]
    result = subprocess.run(command, text=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    print(json.dumps({'status': 'READY', 'documents': documents, 'page_sections': page_sections,
                      'manual_index': str(args.output_index), 'manifest': str(args.output_manifest)}))


if __name__ == '__main__':
    main()
