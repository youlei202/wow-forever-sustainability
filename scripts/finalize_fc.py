"""Finalize document manifests and validate the anonymous compiled artifact."""
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import fitz
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=setup_paths();out=root/'artifacts/final-completion-capacity';paper=out/'paper'
    for path in (SOURCE_ROOT/'docs/final-completion-capacity').glob('*.md'):
        shutil.copy2(path,out/path.name)
    provenance=json.loads((out/'THEORY_PROVENANCE.json').read_text())
    provenance['current_stage_documents']={name:sha(out/name) for name in provenance['current_stage_documents']}
    provenance['digest_scope']='Final maintained document versions. Frozen native run inputs/source snapshots retain their original hashes.'
    atomic_json(out/'THEORY_PROVENANCE.json',provenance)
    manifest=json.loads((out/'REPRODUCTION_MANIFEST.json').read_text())
    sources=set(manifest['sources'])|{'scripts/finalize_fc.py'}
    sources|={str(p.relative_to(SOURCE_ROOT)) for p in (SOURCE_ROOT/'paper').glob('fc_*') if p.is_file()}
    sources|={str(p.relative_to(SOURCE_ROOT)) for p in (SOURCE_ROOT/'paper/fc_sections').glob('*.tex')}
    manifest['sources']={name:sha(SOURCE_ROOT/name) for name in sorted(sources)}
    manifest['pdf_inspection_dependency']={'PyMuPDF':importlib.metadata.version('PyMuPDF')}
    manifest['embedded_database_sha256']=sha(root/'external/mythicsim-forever-engine-r3-variants/assets/database/db.bin')
    atomic_json(out/'REPRODUCTION_MANIFEST.json',manifest)
    freeze=subprocess.run([sys.executable,'-m','pip','freeze'],check=True,text=True,capture_output=True).stdout
    (out/'ENVIRONMENT_FREEZE.txt').write_text(freeze)
    pdf=paper/'fc_main.pdf';document=fitz.open(pdf);texts=[page.get_text() for page in document]
    assert all(abs(page.rect.width-612)<.1 and abs(page.rect.height-792)<.1 for page in document)
    assert all('leiyo' not in text and '/work/' not in text for text in texts)
    assert all('Manuscript under review' not in text for text in texts)
    assert all('??' not in text for text in texts)
    references=next(i+1 for i,text in enumerate(texts) if 'REFERENCES' in text)
    appendix=next(i+1 for i,text in enumerate(texts) if 'EXACT SCALAR COMPLETION PROOFS' in text)
    assert references<=8
    previews=root/'tmp/final-completion-capacity/paper/previews';previews.mkdir(parents=True,exist_ok=True)
    for index in sorted({0,references-1,appendix-1,len(document)-2}):
        document[index].get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(str(previews/f'page_{index+1}.png'))
    for obsolete in paper.glob('preview_page_*.png'):obsolete.unlink()
    log=(root/'logs/final-completion-capacity/paper-build.log').read_text()
    assert 'undefined' not in log.lower()
    tests=(root/'logs/fc-tests-final.log').read_text();assert '121 passed' in tests
    (out/'TEST_RESULTS.txt').write_text(tests)
    with (out/'RACE_CLASS_56_RESULTS.csv').open() as f:coverage=list(csv.DictReader(f))
    assert len(coverage)==56 and len({r['context_id'] for r in coverage})==56
    assert sum(r['faction']=='Alliance' for r in coverage)==28
    assert sum(r['faction']=='Horde' for r in coverage)==28
    assert len({r['class'] for r in coverage})==9
    audit={'status':'pass','pdf':str(pdf),'pdf_sha256':sha(pdf),'pages':len(document),
           'references_start_page':references,'main_content_pages_at_most':references,
           'appendix_start_page':appendix,'paper_size':'US Letter','anonymous_text_check':'pass',
           'submission_status':'Not submitted; template review-status boilerplate overridden without altering template file.',
           'undefined_references':0,'layout_note':'TeX retains a small abstract-box overfull warning and underfull justification warnings; pages visually inspected.',
           'tests_passed':121,'coverage_rows':56,'classes':9,'Alliance_contexts':28,'Horde_contexts':28}
    atomic_json(out/'FINAL_VALIDATION.json',audit);print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
