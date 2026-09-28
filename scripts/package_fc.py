"""Self-contained internal review evidence; no upload or submission."""
import hashlib
import json
from pathlib import Path
import zipfile
from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def main():
    root=setup_paths(); stage='final-completion-capacity'; artifact=root/'artifacts'/stage
    runs=root/'runs'/stage; files={}; native={}
    required=['REVIEW.md','FROZEN_MAIN_PROTOCOL.json','MATCHED_ECOLOGIES.csv',
      'COMPLETION_SPECTRA.csv','THEORY_PREDICTIONS.csv','NATIVE_CAPACITY_RESULTS.csv',
      'DIRECT_REDESIGN_ESCAPE.csv','COMPATIBILITY_ESCAPE.csv','MECHANISM_DIVERSITY.csv',
      'CLASS_FACTION_RESULTS.csv','RACE_CLASS_56_RESULTS.csv','FACTION_SUMMARY.csv',
      'LEGACY_RELEVANCE.csv','PORTFOLIO_COMPLEXITY.csv','COSTS.csv','THEORY.md',
      'RESULTS.md','PRIOR_WORK_DELTA.md','paper/fc_main.pdf']
    for relative in required:
        if not (artifact/relative).is_file():raise FileNotFoundError(relative)
    for path in artifact.rglob('*'):
        if path.is_file() and path.name not in ('PACKAGE_RECEIPT.json','ARCHIVE_MANIFEST.json'):
            files['artifacts/'+str(path.relative_to(artifact))]=path
    for path in runs.rglob('*'):
        if path.is_file() and path.name!='native.frozen':
            files['runs/'+str(path.relative_to(runs))]=path
    for path in sorted(runs.glob('*/RESULTS.json')):
        data=json.loads(path.read_text())
        if 'rows' not in data:continue
        for row in data['rows']:
            if row is not None and row.get('cache_directory'):
                native[row['cache_key']]=Path(row['cache_directory'])
    for key,directory in native.items():
        for path in directory.iterdir():
            if path.is_file():files['native_cache/'+key[:2]+'/'+key+'/'+path.name]=path
    for directory in ('src','configs','scripts','tests','docs'):
        for path in (SOURCE_ROOT/directory).rglob('*'):
            if path.is_file() and path.suffix not in ('.pyc','.pdf','.png','.zip'):
                files['source/'+str(path.relative_to(SOURCE_ROOT))]=path
    for path in (SOURCE_ROOT/'paper').rglob('*'):
        if path.is_file() and (path.name.startswith('fc_') or 'fc_sections' in path.parts):
            files['source/'+str(path.relative_to(SOURCE_ROOT))]=path
    for name in ('README.md','AGENTS.md','pyproject.toml','requirements.lock'):
        files['source/'+name]=SOURCE_ROOT/name
    files['native/wowfs-native-variants']=root/'envs/r3-go/wowfs-native-variants'
    engine=root/'external/mythicsim-forever-engine-r3-variants'
    files['native/LICENSE']=engine/'LICENSE'
    files['inputs/r5-theory/THEORY.md']=root/'inputs/r5-theory/THEORY.md'
    files['inputs/RESEARCH_BRIEF_FINAL_COMPLETION_CAPACITY.md']=root/'inputs/RESEARCH_BRIEF_FINAL_COMPLETION_CAPACITY.md'
    for name in ('aistats2027.sty','sample_paper.tex'):
        files['paper_template/'+name]=root/'external/AISTATS2027PaperPack/AISTATS2027PaperPack'/name
    # Include source and presets needed to rebuild/inspect the exact native
    # engine, excluding its git database, build products and dependency caches.
    allowed={'.go','.mod','.sum','.proto','.json','.md','.txt','.sh','.ts','.bin'}
    for path in engine.rglob('*'):
        if any(part in ('.git','node_modules','dist','build','vendor') for part in path.relative_to(engine).parts):continue
        if path.is_file() and (path.suffix in allowed or path.name=='Makefile' or
                               any(token in path.name.upper() for token in ('LICENSE','NOTICE','COPYING'))):
            files['native/source/'+str(path.relative_to(engine))]=path
    manifest={'scope':'Internal review archive. Contains local provenance paths; not a public anonymous submission.',
              'native_cache_entries':len(native),'entries':{name:{'bytes':p.stat().st_size,'sha256':sha(p)} for name,p in sorted(files.items())}}
    atomic_json(artifact/'ARCHIVE_MANIFEST.json',manifest)
    files['ARCHIVE_MANIFEST.json']=artifact/'ARCHIVE_MANIFEST.json'
    dest=root/'artifacts/WOW_FOREVER_FINAL_COMPLETION_CAPACITY_REVIEW.zip'
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for name,path in sorted(files.items()):
            z.write(path,name,compress_type=zipfile.ZIP_STORED if path.suffix=='.gz' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(dest) as z:
        bad=z.testzip()
        if bad:raise ValueError('Archive CRC failure: '+bad)
    receipt={'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),
             'entries':len(files),'native_cache_entries':len(native),'crc_check':'pass'}
    atomic_json(artifact/'PACKAGE_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
