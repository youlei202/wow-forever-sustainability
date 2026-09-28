"""Native completeness and event receipts only; no ecological success inference."""
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_sequence_analysis import write_csv


def raw_telemetry(pair):
 key,directory=pair
 with gzip.open(Path(directory)/'output.json.gz','rt') as stream:data=json.load(stream)
 return key,data['wowfsResearchWorld']


def main():
 root=setup_paths();out=root/'artifacts/r4-foundational-discovery';base=root/'runs/r4-foundational-discovery/baseline-v1'
 ecology=json.loads((base/'BASE_ECOSYSTEMS.json').read_text());baseline=json.loads((base/'RESULTS.json').read_text())
 coverage=[];rows=baseline['rows'];lookup={}
 for row in rows:
  if row is not None:lookup[(row['gear_id'],row['race'],row['task'],row['strategy'])]=row
 for pool in ecology['ecosystems']:
  for race in ecology['races']:
   for task in ecology['tasks']:
    for strategy in ecology['strategies']:
     keys=[(gid,race,task['id'],strategy['id']) for gid in pool['terminal_gear_ids']]
     completed=[lookup[k] for k in keys if k in lookup]
     coverage.append({'run_id':'baseline-v1','task_scope':'original_eight','world':'native','intervention_id':'baseline','pool':pool['id'],'background':pool['background'],
      'race':race,'task':task['id'],'strategy':strategy['id'],'raw_domain_configurations':pool['raw_terminal_count'],
      'legal_domain_configurations':pool['legal_terminal_count'],'initial_old_configurations':pool['initial_count'],
      'new_item_identities':len(pool['new_source_ids']),'expected_cells':len(keys),'completed_cells':len(completed),
      'missing_cells':len(keys)-len(completed),'logical_battle_exposures':sum(r['iterations'] for r in completed),
      'status':'complete' if len(completed)==len(keys) else 'not_run_or_incomplete',
      'physical_count_scope':'Pool exposures overlap; physical total from independent cache audit.'})
 worldrun=root/'runs/r4-foundational-discovery/worlds-v1';world_progress=worldrun/'PROGRESS.json'
 if world_progress.exists() and json.loads(world_progress.read_text())['status']=='complete':
  result=json.loads((worldrun/'RESULTS.json').read_text());worldrows=result['rows'];groups=defaultdict(list)
  for row in worldrows:
   if row is not None:groups[(row['intervention_id'],row['pool'],row['race'],row['task'],row['strategy'])].append(row)
  pools={p['id']:p for p in ecology['ecosystems']}
  for key,completed in sorted(groups.items()):
   contrast,pid,race,task,strategy=key;pool=pools[pid]
   coverage.append({'run_id':'worlds-v1','task_scope':'original_eight','world':completed[0]['world'],'intervention_id':contrast,'pool':pid,'background':pool['background'],
     'race':race,'task':task,'strategy':strategy,'raw_domain_configurations':pool['raw_terminal_count'],
     'legal_domain_configurations':pool['legal_terminal_count'],'initial_old_configurations':pool['initial_count'],
     'new_item_identities':len(pool['new_source_ids']),'expected_cells':pool['legal_terminal_count'],'completed_cells':len(completed),
     'missing_cells':pool['legal_terminal_count']-len(completed),'logical_battle_exposures':sum(r['iterations'] for r in completed),
     'status':'complete' if len(completed)==pool['legal_terminal_count'] else 'not_run_or_incomplete',
     'physical_count_scope':'Pool exposures overlap; physical total from independent cache audit.'})
  cache={r['cache_key']:r['cache_directory'] for r in worldrows if r}
  telemetry={}
  with ThreadPoolExecutor(max_workers=16) as executor:
   for key,value in executor.map(raw_telemetry,cache.items()):telemetry[key]=value
  events=[]
  for key,completed in sorted(groups.items()):
   totals=Counter();sources=Counter();windows=Counter();n=sum(r['iterations'] for r in completed)
   for row in completed:
    t=telemetry[row['cache_key']];totals.update(t['totals'])
    for source,c in t['by_source'].items():sources[source]+=c['suppressed_reentrant_requested_count']+c['suppressed_heroism_extra_events']
    for window,c in t['by_request_time_window'].items():windows[window]+=c['suppressed_reentrant_requested_count']+c['suppressed_heroism_extra_events']
   events.append(dict(zip(['intervention_id','pool','race','task','strategy'],key))|{
    'world':completed[0]['world'],'native_cells':len(completed),'logical_battle_exposures':n,**dict(totals),
    'heroism_extra_opportunities_per_battle':totals['eligible_heroism_extra_events']/n,
    'suppressed_heroism_events_per_battle':totals['suppressed_heroism_extra_events']/n,
    'suppressed_reentrant_requests_per_battle':totals['suppressed_reentrant_requested_count']/n,
    'suppression_counts_by_source':dict(sources),'suppression_counts_by_request_time_10s_window':dict(windows),
    'scope':'Native trigger/request telemetry; request count is not realized attacks; shared logical cells counted once per comparison context.'})
  write_csv(out/'WORLD_EVENT_TELEMETRY.csv',events)
  atomic_json(out/'WORLD_TELEMETRY_INDEX.json',{'unique_physical_output_keys':len(telemetry),'logical_context_cells':len(worldrows),
    'table_rows':len(events),'source':'Raw wowfsResearchWorld output; unchanged native event summaries remain in cache.',
    'worlds_run':str(worldrun)})
 growthrun=root/'runs/r4-foundational-discovery/task-growth-v1'
 if (growthrun/'RESULTS.json').exists():
  growth=json.loads((growthrun/'RESULTS.json').read_text())
  growth_ecology=json.loads((growthrun/'BASE_ECOSYSTEMS.json').read_text())
  lookup={(r['gear_id'],r['race'],r['task'],r['strategy']):r for r in growth['rows'] if r}
  growth_coverage=[]
  for pool in growth_ecology['ecosystems']:
   for race in growth_ecology['races']:
    for task in growth_ecology['tasks']:
     for strategy in growth_ecology['strategies']:
      keys=[(gid,race,task['id'],strategy['id']) for gid in pool['terminal_gear_ids']]
      completed=[lookup[k] for k in keys if k in lookup]
      growth_coverage.append({'run_id':'task-growth-v1','task_scope':'four_added_demands_separate_diagnostic',
       'world':'native','intervention_id':'task_growth','pool':pool['id'],'background':pool['background'],
       'race':race,'task':task['id'],'strategy':strategy['id'],'raw_domain_configurations':pool['raw_terminal_count'],
       'legal_domain_configurations':pool['legal_terminal_count'],'initial_old_configurations':pool['initial_count'],
       'new_item_identities':len(pool['new_source_ids']),'expected_cells':len(keys),'completed_cells':len(completed),
       'missing_cells':len(keys)-len(completed),'logical_battle_exposures':sum(r['iterations'] for r in completed),
       'status':'complete' if len(completed)==len(keys) else 'not_run_or_incomplete',
       'physical_count_scope':'Pool exposures overlap; physical total from independent cache audit.'})
  coverage.extend(growth_coverage)
  write_csv(out/'TASK_GROWTH_COMBINATION_COVERAGE.csv',growth_coverage)
 write_csv(out/'FULL_COMBINATION_COVERAGE.csv',coverage)
 print(json.dumps({'coverage_rows':len(coverage),'missing_cells':sum(r['missing_cells'] for r in coverage),
  'logical_cell_exposures':sum(r['completed_cells'] for r in coverage),'scope':'Physical deduplicated counts are separate.'}))

if __name__=='__main__':main()
