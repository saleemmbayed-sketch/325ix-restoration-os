# BMW 325iX V4 — Visual, linked workshop dataset

Version 4.0.0. **V3.1 is complete: 805 source assemblies, 13,845 parts-table records, 7,190 distinct part numbers, 805 figure occurrences, 572 unique drawing URLs.** These data were read from your existing Drive corpus, not inferred from web search. This collector does **not** overwrite V3.

## Goals and evidence limitations

- Acquire publicly accessible illustration binaries via direct HTTPS links already extracted in V3, only if site robots/access controls permit.
- Download each unique illustration URL **once**, storing SHA-256, pixel dimensions, byte size, MIME type, source URL and success/failure state.
- Link **805 figure occurrences** to shared image assets, and each of **13,845 part-table rows** to its assembly drawing and printed callout number.
- Enable local exact part-number search and multilingual-compatible SQLite FTS indexing; produce a standalone HTML visual atlas.
- Flag date restrictions against **December 1987** for your BMW 325iX LHD manual sedan. This flag is an approximate reading of textual date windows, **not proof of actual fitment**. Options, manual-vs-automatic and as-installed component identity must be verified.
- Optionally index photographs provided by the workshop and place them under the exact 11-digit BMW number, without falsely claiming automatic visual identification.

**Not provided yet:** individual supplier part photos for all 7,190 part numbers, accurate image *pixel locations* of diagram callouts, official verified repair torques/tolerances, automatic interchange certification, offline imagery for sources where download is blocked. A diagram may cover multiple catalog assemblies. Never equate image similarity with mechanical compatibility.

## Use your existing Colab notebook (no new notebook)

1. Confirm V3.1's `coverage.json` reports `retrieved=805`; it does, based on the supplied log.
2. Save `325ix_v4_visual_index.py` into Google Drive `325IX DATA/09_RAG_DATASETS_AND_INGESTION/`.
3. Open the **same V3.1 Colab notebook** you used before. Add ONE new code cell at the end; paste `PASTE_ONCE_IN_EXISTING_V3_1_COLAB.py` into it.
4. Run that cell **alone**, not `Runtime → Run all`. The default `V4_MAX_NEW_IMAGES = 25` tests the image host conservatively. When successful, change to `0` for every remaining image.
5. Download progress is checkpointed per image, so rerunning the cell skips saved binaries. Inspect `v4_coverage.json` and `v4_collector.log` for counts/errors.

## Run locally on macOS / Linux

Once your existing complete `325IX DATA` folder is present locally:

```bash
python3 -m venv ~/.venvs/bmw325ix
~/.venvs/bmw325ix/bin/python -m pip install requests pillow
~/.venvs/bmw325ix/bin/python /path/to/325ix_v4_visual_index.py --root "$HOME/Downloads/325IX DATA" --download-images --max-images 25
```

Then, to continue all remaining images:

```bash
~/.venvs/bmw325ix/bin/python /path/to/325ix_v4_visual_index.py --root "$HOME/Downloads/325IX DATA" --download-images --max-images 0
```

Run `--root ...` with **no** `--download-images` for a no-network offline metadata/search rebuild.

## V4 outputs

New work lives under `325IX DATA/14_MULTIMODAL_MEDIA_AND_GRAPH/`, preserving existing specification files:

- `01_DIAGRAM_IMAGES/`: downloaded actual WebP/PNG/JPEG files, named by **SHA-256** of content; byte-for-byte content duplicates are saved once.
- `02_PART_PHOTOS/<11-digit-BMW-part-number>/`: drop your own phone/workshop part photographs here. V4 verifies file readability and links them to the number *as filed*, while keeping `identity_verified=false` until reviewed. Unlabeled pictures can go in `02_PART_PHOTOS/unmatched/`.
- `03_MANIFESTS/image_assets.jsonl`: one record per remote image URL and local status.
- `03_MANIFESTS/figure_occurrences.jsonl`: drawing instances joined to their assembly records.
- `03_MANIFESTS/parts_to_figures.jsonl`: part row → assembly → figure → image asset graph; exact **pixel-location annotation is not yet performed**.
- `03_MANIFESTS/part_photo_research_queue.csv`: 7,190 part numbers ranked for external photo research.
- `03_MANIFESTS/v4_coverage.json`: exact current progress.
- `03_MANIFESTS/image_acquisition_state.json`: resumable per-image state; do not delete.
- `04_SEARCH/325ix_multimodal.sqlite3`: normalized relational database + FTS5 full-text search.
- `OFFLINE_VISUAL_ATLAS.html`: searchable illustrations, catalog part rows, callout positions, OEM numbers and links. It works offline with images once downloaded and when the folder structure is kept together.

### Browser viewer note

Google Drive previews do not reliably resolve relative `01_DIAGRAM_IMAGES/` paths from an HTML file. For true offline browsing, download the **entire** V4 directory to your Mac/PC and open `OFFLINE_VISUAL_ATLAS.html` locally. The standalone HTML works for text and metadata even before image downloads, with direct source-image URLs available when online.

### Resumability and polite access

V4 makes normal requests to documented source image URLs, verifies actual image content, respects robots rules, refuses unknown hosts and unexpected redirects, and logs server errors without bypassing restrictions. It does not scrape behind sign-ins, CAPTCHAs or paywalls. Personal use affects how you organize the archive but is not a guarantee of permission to mirror a website.

### Vehicle configuration

Use VIN `VIN_NOT_CONFIGURED`, 1987-12-10 factory production, Swiss/ECE LHD 4-door manual AWD, **owner-confirmed replacement M20B25**. The generic European parts catalog also includes other dates, transmissions and options. Do not treat its rows as automatically applicable to your specific as-built vehicle.
