"""Metric invariants: unresolved, not-run and correlated trials stay distinct."""
import unittest
import tempfile
from pathlib import Path
import json

from wowfs.experiments.co_benchmark_report import compute_existence_metrics, compute_prefixes, compute_query_metrics, dump_csv, read_csv, cluster_metadata, clustered_log_ratio, prefix_cost_plot_data


class BenchmarkReportTests(unittest.TestCase):
    def test_cost_panels_match_histories_truncate_exhaustion_and_retain_unknown(self):
        methods=('reference_fresh','reference_cached','reference_interface','sat_incremental','sat_interface')
        histories=[];prefixes=[]
        for identity,n,kind in [('s1',2,'SYNTHETIC_EXACT'),('s2',3,'SYNTHETIC_EXACT'),('n1',2,'NEW_NATIVE_MEAN')]:
            for method in methods:
                histories.append({'suite':'s','instance_id':identity,'method':method,'data_kind':kind,
                    'status':'COMPLETE','elapsed_seconds':9,'registered_queries':n})
                for length in (1,n):
                    partial=identity=='s2' and method=='reference_interface' and length==n
                    prefixes.append({'suite':'s','instance_id':identity,'method':method,'prefix':length,
                        'elapsed_spent_seconds':9 if partial else length,'resolved_correct':1 if partial else length,
                        'all_targets_resolved':not partial,'within_history_budget':True})
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);(out/'figures').mkdir();prefix_cost_plot_data(out,prefixes,histories)
            rows=read_csv(out/'QUERY_AGGREGATE_PREFIX_COSTS.csv')
        r=next(r for r in rows if r['data_kind']=='SYNTHETIC_EXACT' and r['method']=='reference_interface' and r['requested_prefix_per_history']=='10')
        self.assertEqual(int(r['total_requested']),5)
        self.assertEqual(int(r['resolved_correct']),3)
        self.assertEqual(float(r['total_spent_seconds']),11)
        self.assertEqual(r['all_targets_resolved_within_budget'],'False')
        native=next(r for r in rows if r['data_kind']=='NEW_NATIVE_MEAN' and r['method']=='reference_interface' and r['requested_prefix_per_history']=='10')
        self.assertEqual(int(native['matched_histories']),1)
        self.assertEqual(int(native['total_requested']),2)

    def test_related_native_histories_do_not_create_catalogue_interval(self):
        rows=[]
        for family in ('glove','trinket'):
            for variant in ('good','bad'):
                identity=family+'__'+variant
                raw={'data_kind':'INHERITED_NATIVE_MEAN','family':family}
                base={**raw,**cluster_metadata(raw,identity),'instance_id':identity,'workflow':'unknown_y','suite':'s',
                      'budget_seconds':60,'status':'YES'}
                rows.extend([{**base,'method':'reference','elapsed_seconds':.2},{**base,'method':'sat','elapsed_seconds':.1}])
        result=clustered_log_ratio(rows,'reference','sat')
        self.assertEqual(result['common_solved_pairs'],4)
        self.assertEqual(result['history_clusters'],2)
        self.assertIsNone(result['descriptive_cluster_bootstrap_95pct'])
        self.assertAlmostEqual(result['history_balanced_geometric_ratio'],2)

    def test_par2_and_denominators(self):
        base={'solver_seed':0,'data_kind':'SYNTHETIC_EXACT','workflow':'unknown_y','family':'f','method':'sat',
              'budget_seconds':60,'suite':'s','peak_rss_bytes':1,'seed_semantics':'deterministic_repeat_label'}
        rows=[]
        for j,(status,elapsed) in enumerate([('YES',2),('UNKNOWN_TIMEOUT',60),('UNKNOWN_MEMORY',3),('NOT_RUN',None),('INVALID_INITIAL',.01)]):
            rows.append({**base,'instance_id':str(j),'history_cluster_id':str(j),'status':status,'elapsed_seconds':elapsed})
        result=compute_existence_metrics(rows)
        g=next(g for g in result['groups'] if g['family']=='all_families')
        self.assertEqual(g['par2_mean_seconds'],242/3)
        self.assertEqual(g['eligible_executed'],3)
        self.assertEqual(g['resolved_within_wall_cap'],1)
        self.assertEqual(g['not_run_excluded_from_PAR2'],1)

    def test_partial_work_does_not_become_completion_time(self):
        hs=[];rs=[]
        for method in ('reference_interface','sat_incremental'):
            hs.append({'suite':'s','instance_id':'i','family':'f','data_kind':'SYNTHETIC_EXACT','method':method,
                'registered_queries':10,'prefixes':[1,10],'elapsed_seconds':900,'preparation_seconds':720,
                'interface_complete':False if method.endswith('interface') else None,'status':'UNKNOWN_TIMEOUT'})
            rs.append({'suite':'s','instance_id':'i','method':method,'query_kind':'singleton','status':'UNKNOWN_TIMEOUT' if method.endswith('interface') else 'YES',
                       'query_index':1,'cumulative_seconds':721})
        prefixes=compute_prefixes(rs,hs)
        p=next(p for p in prefixes if p['method']=='reference_interface' and p['prefix']==10)
        self.assertEqual(p['not_processed'],9);self.assertEqual(p['resolved_correct'],0)
        self.assertEqual(p['elapsed_spent_seconds'],900);self.assertFalse(p['all_targets_resolved'])
        metrics=compute_query_metrics(rs,hs,prefixes)
        self.assertTrue(all(r['observed_break_even_prefix'] is None for r in metrics['break_even']))

    def test_crossing_requires_matching_resolution_within_history_budget(self):
        hs=[{'suite':'s','instance_id':'i','method':m,'status':'COMPLETE','registered_queries':10,
             'data_kind':'SYNTHETIC_EXACT','family':'f'} for m in ('reference_interface','sat_incremental')]
        prefixes=[]
        for m,t,within in [('reference_interface',8,True),('sat_incremental',10,True)]:
            prefixes.append({'suite':'s','instance_id':'i','method':m,'prefix':1,'all_targets_resolved':True,
                             'within_history_budget':within,'elapsed_spent_seconds':t,'resolved_correct':1})
        metrics=compute_query_metrics([],hs,prefixes)
        pair=next(r for r in metrics['break_even'] if r['compiled_method']=='reference_interface' and r['online_method']=='sat_incremental')
        self.assertEqual(pair['observed_break_even_prefix'],1)
        prefixes[0]['within_history_budget']=False
        metrics=compute_query_metrics([],hs,prefixes)
        pair=next(r for r in metrics['break_even'] if r['compiled_method']=='reference_interface' and r['online_method']=='sat_incremental')
        self.assertIsNone(pair['observed_break_even_prefix'])

    def test_complete_partial_interface_is_not_fully_resolved(self):
        h={'suite':'s','instance_id':'i','method':'sat_interface','status':'COMPLETE',
           'registered_queries':2,'data_kind':'SYNTHETIC_EXACT','family':'f'}
        rows=[{**h,'query_kind':'singleton','query_index':i,'status':status} for i,status in enumerate(('YES','UNKNOWN_TIMEOUT'),1)]
        result=compute_query_metrics(rows,[h],[])
        s=result['by_table_kind_and_method'][0]
        self.assertEqual(s['workflow_status_counts'],{'COMPLETE':1})
        self.assertEqual(s['resolved_queries'],1)
        self.assertEqual(s['complete_workflows_with_all_queries_resolved'],0)
        self.assertEqual(s['complete_workflows_with_unresolved_queries'],1)

    def test_csv_roundtrip_preserves_core_metrics(self):
        base={'solver_seed':0,'data_kind':'SYNTHETIC_EXACT','workflow':'unknown_y','family':'f',
              'budget_seconds':60,'suite':'s','peak_rss_bytes':1,'seed_semantics':'deterministic_repeat_label',
              'instance_id':'i','history_cluster_id':'h','mandatory_global_cap_violation':False}
        rows=[{**base,'method':'reference','status':'YES','elapsed_seconds':.2},
              {**base,'method':'sat','status':'YES','elapsed_seconds':.1},
              {**base,'method':'cp_sat','status':'UNKNOWN_MEMORY','elapsed_seconds':None}]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'rows.csv';dump_csv(p,rows)
            restored=read_csv(p)
        self.assertEqual(compute_existence_metrics(rows),compute_existence_metrics(restored))


if __name__=='__main__':unittest.main()
