# Paste this whole block into ONE NEW CODE CELL at the bottom of your EXISTING V3.1 notebook.
# Do not create a new Colab notebook. Run this cell whenever V4 needs to resume.
# It reads V3.1's completed 805 assemblies; it will NOT rerun V3.1 or refetch its pages.
import sys, subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path('/content/drive/MyDrive/325IX DATA')
SCRIPT = ROOT/'09_RAG_DATASETS_AND_INGESTION'/'325ix_v4_visual_index.py'

if not ROOT.is_dir():
    from google.colab import drive
    drive.mount('/content/drive')

assert SCRIPT.is_file(), f'Missing V4 script: {SCRIPT}. Upload it to 09_RAG_DATASETS_AND_INGESTION.'
subprocess.run([sys.executable,'-m','pip','install','-q','requests>=2.31,<3','pillow>=10,<13'],check=True)

# Set 25 for an initial download test, or 0 for ALL remaining figure images.
V4_MAX_NEW_IMAGES = 25

CMD = [sys.executable,'-u',str(SCRIPT),'--root',str(ROOT),
       '--download-images','--max-images',str(V4_MAX_NEW_IMAGES),
       '--delay','1.5','--timeout','35']
print('V4 command:', ' '.join(CMD), flush=True)
LOG = ROOT/'14_MULTIMODAL_MEDIA_AND_GRAPH'/'03_MANIFESTS'/'v4_collector.log'
LOG.parent.mkdir(parents=True,exist_ok=True)
with LOG.open('a',encoding='utf-8') as f:
    f.write(f'\n=== {datetime.utcnow().isoformat()}Z ===\n')
    process=subprocess.Popen(CMD,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    for line in process.stdout:
        print(line,end='',flush=True)
        f.write(line)
    code=process.wait()
print('V4 exit code:',code,'— log saved:',LOG)
if code:
    raise RuntimeError('V4 failed; see actual traceback in log above.')

COVERAGE=ROOT/'14_MULTIMODAL_MEDIA_AND_GRAPH'/'03_MANIFESTS'/'v4_coverage.json'
if COVERAGE.is_file():
    import json
    print('\nV4 coverage:')
    d=json.loads(COVERAGE.read_text(encoding='utf-8'))
    for k in ['v3_assemblies','parts_rows','distinct_part_numbers',
              'figure_associations','unique_image_assets','image_assets_saved',
              'unique_binary_contents_saved','image_status_breakdown',
              'workshop_photos_indexed']:
        print(f'  {k}: {d.get(k)}')
