"""Compact review handoff; preserve full results, omit bulk reproduction data.

Creates separate outputs. Never rewrites the completed study or its archive.
"""
import ast
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import zipfile

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


PROMPT='''Review the attachments as a rigorous research reviewer. Prioritize issues that could overturn the central conclusions, rather than accommodating positive conclusions.
Check: (1) the exact theorem's reachable families, endpoints, minimum amplitude, nonmonotone releases, and legacy-source conditions; (2) strict separation of conditional continuous upper bounds, finite mean oracles, and prospectively supported lower bounds; (3) propagation of paired-t intervals through the optimized frontier and source relevance, within-context multiple comparisons, and the fixed-reference estimand; (4) the chronology of frozen designs and subsequent sensitivity analyses; (5) negative mechanism results, Warlock not_run paths, original D, racial omissions, and all denominators; (6) the actual contribution beyond prior literature.
List issues by severity, identifying the file, table or formula, evidence, impact, and smallest correction for each. End with the strongest defensible claim and statements that must be weakened. Do not claim to have independently rechecked every raw execution merely because a summary reports a passing audit. If code or raw data are missing, identify the specific missing files.
'''


def local_sources(seeds):
    """Include local Python imports transitively, without external dependencies."""
    seen=set();pending=list(seeds)
    while pending:
        p=pending.pop().resolve()
        if p in seen or not p.is_file():continue
        seen.add(p)
        if p.suffix!='.py':continue
        for node in ast.walk(ast.parse(p.read_text())):
            names=([node.module] if isinstance(node,ast.ImportFrom) and node.module else
                   [alias.name for alias in node.names] if isinstance(node,ast.Import) else [])
            for name in names:
                if not name.startswith('wowfs'):continue
                base=SOURCE_ROOT/'src'/name.replace('.','/')
                candidate=base.with_suffix('.py') if base.with_suffix('.py').exists() else base/'__init__.py'
                pending.append(candidate)
        for parent in p.parents:
            if parent==SOURCE_ROOT:break
            init=parent/'__init__.py'
            if init.exists():pending.append(init)
    return seen


def main():
    root=setup_paths();original=root/'artifacts/final-completion-capacity'
    dest=root/'artifacts/final-completion-capacity-gpt-pro';dest.mkdir(exist_ok=True)
    zip_path=root/'artifacts/WOW_FOREVER_FINAL_COMPLETION_CAPACITY_GPT_PRO.zip'
    source_receipt=json.loads((original/'PACKAGE_RECEIPT.json').read_text())
    shutil.copy2(original/'paper/fc_main.pdf',dest/'01_PAPER.pdf')
    # All448 rows and every existing column are kept byte-for-byte, including
    #20 not_run exact paths and all failed/uncertain attempted sequences.
    shutil.copy2(original/'SEQUENCE_CAPACITY_SUMMARY.csv',dest/'03_ALL_SEQUENCES.csv')
    with (dest/'03_ALL_SEQUENCES.csv').open() as f:sequences=list(csv.DictReader(f))
    assert len(sequences)==448 and len({r['context_id'] for r in sequences})==56
    assert sum(r['status']=='not_run_nonaffine_exact_path' for r in sequences)==20
    dossier='''# GPT Pro Review Materials: Completion Capacity

## Three files recommended for direct upload

1. `01_PAPER.pdf`: the complete anonymous manuscript, including proofs and a coverage heatmap; not submitted.
2. `02_REVIEW_DOSSIER.md`: this file, containing the review task, complete current theory, result boundaries, and negative mechanism results.
3. `03_ALL_SEQUENCES.csv`: a byte-for-byte copy of the original sequence summary, with 56 contexts ×8 paths =448 rows, including every failure, unresolved outcome, and all 20 not_run paths.

A compact evidence ZIP is also available. It contains all published result CSVs, original analysis JSONs, source code/tests, frozen protocols and source code for six physical runs, a small set of native output examples, and a checksum manifest. Consult it for code and source-by-source checks. The three files above are sufficient to begin substantive review without loading every archived JSON into the context at once.

## Review request to copy

'''+PROMPT+'''
## Numbers and boundaries to distinguish before reading

| Object | Numbers | Meaning |
|---|---|---|
| Abstract exact nominal model | 5/2/5/4 | Large-gap/dense/weaker-direct/fixed-budget; excludes original behavioral D |
| Prospectively supported native paths in 51 validated affine contexts | 4/1/4/3 | Lower bounds for value and legacy-source preservation, not exact continuous capacity |
| Mean oracle over the full finite candidate set on independent samples | 4/1/4; budget 33×4+18×3 | Arbitrary release order allowed; maximum capacity is neither continuous nor confidence-guaranteed |
| Conditional continuous dense upper bound | All 51 ≤2 | Assumes a common positive affine response and a fixed common cutoff throughout the declared family; finite validation cannot prove global structure |
| Execution coverage | 9 classes, 56 contexts, 8 tasks | Five Warlock contexts fail scalar mapping; seven contexts have missing racial implementations |
| Original Warrior D | Mean failure in 274/274 attempted stages | No complete seven-condition sequence; different features from other classes cannot replace original D |
| Three event-changing mechanism families | No nonempty complete prospective path passes every interval check | Complete execution does not imply universal theoretical transfer |
| Continued expansion from a fixed history | Point-model remaining upper bound 0 for 51 robust dense histories; interval support in 35 | The other 16 remain unresolved; prospective interventions cannot refund consumed headroom |

- Approximate 95% simultaneous paired-t coverage applies within each context, not jointly across all 56 at 95%; seeds are not independent research units.
- Zero failed physical calls does not mean zero scientific failures or unexecuted designs. The 20 exact Warlock paths were not run, but all finite cross-tables for their robust paths were executed.
- Equal current optimal values do not mean every value in the old ecologies is equal; the interior suboptimal-response distribution is the deliberately varied independent variable.
- The compatibility rule has opportunity costs. The generic model with the same two features contains this rule, so no algorithmic advantage can be claimed.
- The text below and the manuscript contain claims to review, not correctness conclusions the reviewer should accept in advance.

## What the compact materials can and cannot verify

They can verify mathematical arguments, statistical and planning source code, consistency across result tables, complete failure/unresolved denominators, differences between frozen versions and current analysis code, and representative native request/output formats.

The compact package alone cannot recheck all 22,032 native executions: the complete raw cache, full JOBS/RESULTS, native executable, external engine tree, and 19MB full archive manifest are not redistributed here. Existing audit reports are retained as records and must not be equated with independent verification completed during this review. The original 1.1GB full reproduction package is unchanged; specific raw outputs can be added by context/task/cache key.

## Sequence-table field guide

- `mean_successful_prefix` / `empirical_prefix`: two column names for the same mean-passing prefix.
- `ci_supported_prefix` / `confirmed_prefix`: a supported prefix lower bound under the conditional model and declared interval method; 0 does not mean global capacity equals 0.
- `continuous_utility_upper` / `conditional_upper`: frozen fitted-model predictions, not independent-sample continuous upper-bound certificates. The latter are reported separately in the evidence package's `CAPACITY_UPPER_BOUND_CERTIFICATES.csv`.
- Preserve `status=not_run_nonaffine_exact_path` and empty values; never zero-fill them.
- `variant=exact` denotes a prespecified endpoint attempt; `variant=interior` denotes a prespecified path with margin. Both were frozen before confirmation.
- `Warrior_joint_mean_prefix` is only a mean diagnostic of original Warrior D; blanks for other classes mean unevaluated.

## Original package identity

'''+f"Full package file: `{Path(source_receipt['path']).name}`\n\nSHA-256: `{source_receipt['sha256']}`\n\n"+'''
The following sections concatenate existing files in full, without selecting only positive conclusions. Original files are retained in the package for comparison.
'''
    docs=['REVIEW.md','RESULTS.md','THEORY.md','FINITE_REFERENCE_AND_UPPER_BOUNDS.md',
          'MECHANISM_CAPACITY.md','PRIOR_WORK_DELTA.md','ABSTRACT_STRESS.md']
    for name in docs:dossier+=f'\n\n---\n\n# Original file: {name}\n\n'+(original/name).read_text()
    dossier+='\n\n---\n\n# Frozen main protocol (unchanged)\n\n```json\n'+(original/'FROZEN_MAIN_PROTOCOL.json').read_text()+'\n```\n'
    dossier+='\n\n# File-format reference\n\nOfficial documentation describes attaching documents, PDFs, spreadsheets, and data exports. This delivery prioritizes those directly readable files, does not depend on ZIP support, and does not treat API upload limits as ChatGPT Pro limits. Reference: https://learn.chatgpt.com/docs/use-chatgpt\n'
    (dest/'02_REVIEW_DOSSIER.md').write_text(dossier)
    (dest/'REVIEW_PROMPT.txt').write_text(PROMPT)
    files={p.name:p for p in dest.iterdir() if p.is_file() and p.name in ('01_PAPER.pdf','02_REVIEW_DOSSIER.md','03_ALL_SEQUENCES.csv','REVIEW_PROMPT.txt')}
    for path in original.rglob('*'):
        if path.is_file() and path.name!='ARCHIVE_MANIFEST.json' and path.suffix!='.png':
            files['evidence/'+str(path.relative_to(original))]=path
    # Preserve exact source versions used by the physical runs and separate
    # analysis snapshots, but not the repeatedly embedded raw tables.
    runs=root/'runs/final-completion-capacity'
    for path in runs.rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(runs)
        if path.name in ('PROTOCOL.json','FREEZE_TIME.json','PROGRESS.json') or 'source' in relative.parts or path.suffix=='.py':
            files['frozen_runs/'+str(relative)]=path
    seeds=list((SOURCE_ROOT/'src/wowfs/experiments').glob('fc_*.py'))+list((SOURCE_ROOT/'tests').glob('test_fc_*.py'))
    seeds+=list((SOURCE_ROOT/'scripts').glob('*fc*.py'))
    for path in local_sources(seeds):files['source/'+str(path.relative_to(SOURCE_ROOT))]=path
    for directory,pattern in [('configs','fc*'),('configs','final_completion_capacity.json'),('configs','official_contexts.yaml'),('configs','paths.yaml'),('scripts','*fc*.sh')]:
        for path in (SOURCE_ROOT/directory).glob(pattern):
            if path.is_file():files['source/'+str(path.relative_to(SOURCE_ROOT))]=path
    for relative in ['scripts/env.sh','scripts/native_build_r3.sh','src/wowfs/simulator/r3_variants.go','requirements.lock','pyproject.toml','AGENTS.md']:
        files['source/'+relative]=SOURCE_ROOT/relative
    files['formal_input/r5-theory/THEORY.md']=root/'inputs/r5-theory/THEORY.md'
    files['formal_input/RESEARCH_BRIEF_FINAL_COMPLETION_CAPACITY.md']=root/'inputs/RESEARCH_BRIEF_FINAL_COMPLETION_CAPACITY.md'
    # Deterministic examples, chosen by named contexts/tasks/anchor roles,
    # not by whether an output supports the desired result.
    data=json.loads((runs/'capacity-confirmation-v1/RESULTS.json').read_text())
    examples=[]
    for row in data['rows']:
        if row['context_id'] not in ('Alliance_Human_Warrior','Alliance_Human_Warlock'):continue
        if row['task'] not in ('sustained','short_burst','endurance'):continue
        if not set(row['roles'])&{'fit_zero','fit_high','fixed_old_reference'}:continue
        cache=Path(row['cache_directory']);prefix='native_examples/'+row['cache_key']
        examples.append({k:row[k] for k in ('context_id','task','primary_coefficient','partner_coefficient','roles','cache_key','iterations')})
        for name in ('input.json','summary.json','invocation.json','output.json.gz'):files[prefix+'/'+name]=cache/name
    assert len(examples)==18
    atomic_json(dest/'NATIVE_EXAMPLE_INDEX.json',{'selection':'Two named contexts ×three tasks ×three anchor/reference roles; selection independent of outcomes.',
        'scope':'Examples only; not a substitute for a22,032-cell execution audit.','rows':examples})
    files['NATIVE_EXAMPLE_INDEX.json']=dest/'NATIVE_EXAMPLE_INDEX.json'
    readme='''# Compact Review Package

Start with 01_PAPER.pdf, 02_REVIEW_DOSSIER.md, and 03_ALL_SEQUENCES.csv.
REVIEW_PROMPT.txt contains an independent review request to copy. Source code is in source/, frozen execution versions in frozen_runs/, and result tables and audit records in evidence/.

All original result CSVs and analysis JSONs are retained, including negative results, unresolved outcomes, and not_run entries. The full native cache, complete duplicated JOBS/RESULTS, native binary, external engine tree, and original 19MB manifest are omitted. This is scientific review material, not a standalone complete reproduction environment. The 18 native examples selected by named rules allow interface/output checks and cannot replace a full audit.

MANIFEST.json lists the SHA-256 and source path of every file in this package. The original 1.1GB full package is unchanged.
'''
    (dest/'README.md').write_text(readme);files['README.md']=dest/'README.md'
    manifest={'purpose':'Compact scientific review, not complete physical reproduction.','original_archive':source_receipt,
        'retained_sequence_rows':448,'retained_not_run_sequence_rows':20,'native_example_cells':18,
        'omitted':['full native_cache','all native binaries','external native engine checkout','full run JOBS/RESULTS and repeated analysis dumps','original full ARCHIVE_MANIFEST.json','duplicate PNG versions of PDF figures'],
        'files':{name:{'bytes':p.stat().st_size,'sha256':digest(p),'source_path':str(p)} for name,p in sorted(files.items())}}
    atomic_json(dest/'MANIFEST.json',manifest);files['MANIFEST.json']=dest/'MANIFEST.json'
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,path in sorted(files.items()):z.write(path,name)
    with zipfile.ZipFile(zip_path) as z:
        assert z.testzip() is None
        assert z.read('03_ALL_SEQUENCES.csv')==(original/'SEQUENCE_CAPACITY_SUMMARY.csv').read_bytes()
        assert z.read('01_PAPER.pdf')==(original/'paper/fc_main.pdf').read_bytes()
        assert len([n for n in z.namelist() if n.startswith('evidence/') and n.endswith('.csv')])==len(list(original.glob('*.csv')))
    receipt={'zip':str(zip_path),'bytes':zip_path.stat().st_size,'sha256':digest(zip_path),
        'original_bytes':source_receipt['bytes'],'reduction_percent':100*(1-zip_path.stat().st_size/source_receipt['bytes']),
        'zip_entries':len(files),'crc_check':'pass','original_result_tables_unchanged':True,
        'direct_upload_files':{p.name:{'path':str(p),'bytes':p.stat().st_size} for p in sorted(dest.glob('0*'))}}
    atomic_json(dest/'PACKAGE_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
