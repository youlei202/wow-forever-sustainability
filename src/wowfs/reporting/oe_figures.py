"""Auditable vector panels for the open native exploration campaign.

Figures are descriptive readers of frozen analysis products. This module never
runs native simulations, selects thresholds, reconstructs responses, or changes
confirmation decisions. Development point estimates and confirmation intervals
are separate. Missing confirmation is not a zero response.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
import numpy as np


LABELS = {
    'mana_regen': 'Mana regeneration', 'melee_hit': 'Melee hit',
    'spell_hit': 'Spell hit', 'crit_flurry': 'Critical hits / Flurry',
    'weapon_cadence': 'Weapon cadence', 'periodic_refresh': 'Periodic refresh',
    'nature_proc': 'Nature proc', 'shadow_proc': 'Shadow proc',
    'onuse_shared_cd': 'On-use / shared cooldown', 'policy_resource': 'Resource policy',
    'resistance_penetration': 'Resistance / penetration', 'joint_slots': 'Two-slot interaction',
    'catalog_warrior_weapon_type': 'Warrior weapon types',
    'catalog_rogue_weapon_type': 'Rogue weapon types',
    'catalog_heroism_threshold': 'Heroism set',
    'catalog_magister_threshold': 'Magister set',
    'catalog_mage_trinkets': 'Mage trinkets / off-hand',
    'catalog_warlock_weapons': 'Warlock weapons',
}
BLUE, ORANGE, GREEN, GREY = '#0072B2', '#D55E00', '#009E73', '#7A8288'
SOURCE_LABELS = {'magister_history': 'Magister catalog', 'trinket_history': 'Trinket catalog',
                 'penetration_joint': 'Mage: penetration variant', 'mana_joint': 'Druid: mana variant'}


def read_json(path):
    return json.loads(Path(path).read_text())


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows):
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list, tuple))
                             else value for key, value in row.items()})


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def style():
    plt.rcParams.update({'font.size': 9, 'axes.titlesize': 10, 'axes.labelsize': 9,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
                         'savefig.bbox': 'tight', 'axes.axisbelow': True,
                         'axes.titleweight': 'normal', 'grid.color': '#E5E8EB'})


def save(fig, output, name, caption, sources):
    for suffix in ('pdf', 'svg', 'png'):
        fig.savefig(output / f'{name}.{suffix}', dpi=200, facecolor='white')
    plt.close(fig)
    write_json(output / f'{name}_PROVENANCE.json', {
        'caption': caption,
        'source_files': [{'path': str(Path(path).resolve()), 'sha256': sha256(path)} for path in sources],
        'uncertainty': 'Intervals, when present, are read from the independent confirmation analysis. '
                       'Development figures contain point estimates only.',
        'normalization': 'When displayed as percentages, all contrast limits are divided by the '
                         'same observed positive old-reference mean. This is a display rescaling, not a ratio CI.',
        'reporting_source_sha256': sha256(__file__),
    })


def complete_confirmation(folder):
    """Require the complete, audited caller output; never plot partial claims."""
    if folder is None or not (folder / 'SUMMARY.json').exists():
        return [], None
    summary = read_json(folder / 'SUMMARY.json')
    if summary.get('status') != 'completed' or not summary.get('pre_outcome_freeze_verified'):
        raise ValueError('Confirmation figures require a completed analysis with a verified pre-outcome freeze')
    if (folder / 'FAILED.json').exists():
        raise ValueError('Refuse a confirmation directory containing FAILED.json')
    claims = [read_json(folder / row['file']) for row in summary['claims']]
    if any(row.get('status') != 'analysis_completed' or not row.get('pre_outcome_freeze_verified') for row in claims):
        raise ValueError('Incomplete or unaudited confirmation claim')
    return claims, read_json(folder / 'FROZEN_MANIFEST.json')


def coverage(run, output, claims, manifest, confirmation):
    sources = [run / 'WORLD_REGISTRY.jsonl', run / 'WORLD_REGISTRY_CATALOG.jsonl']
    worlds = [world for path in sources for world in jsonl(path)]
    ids = {world['world_id']: world for world in worlds}
    measured = defaultdict(set)
    complete = defaultdict(set)
    for batch in ('broad-v2', 'refine-v1', 'catalog-v1', 'deep-challenge-v1'):
        file = run / 'batches' / batch / 'RESULTS.json'
        if not file.exists():
            continue
        data = read_json(file)
        if data.get('status') != 'completed' or data.get('errors'):
            continue
        sources.append(file)
        cells = defaultdict(set)
        for row in data['rows']:
            if row is None or row.get('world_id') not in ids:
                continue
            if row.get('observed_or_reconstructed') != 'observed':
                raise ValueError('Coverage accepts only actual native observations')
            world_id = row['world_id']
            cells[world_id].add(tuple(row[key] for key in ('candidate_id', 'partner_id', 'task_id', 'policy_id')))
        for world_id, identities in cells.items():
            measured[world_id].add(batch)
            w = ids[world_id]
            expected = len(w['candidates']) * len(w['partners']) * len(w['tasks']) * len(w['policies'])
            if len(identities) == expected:
                complete[world_id].add(batch)
        del data
    confirmed = defaultdict(lambda: {'local': set(), 'heldout': set()})
    if claims:
        world_meta = {w['world_id']: w for w in manifest['worlds']}
        for claim in claims:
            world = world_meta[claim['world_id']]
            split = 'heldout' if claim['claim_id'].endswith('__heldout') else 'local'
            confirmed[world['mechanism_id']][split].add(claim['world_id'])
        sources += [confirmation / 'SUMMARY.json', confirmation / 'FROZEN_MANIFEST.json']
    audit_path = run / 'FACTION_GEAR_AUDIT.json'
    flagged = set()
    if audit_path.exists():
        sources.append(audit_path)
        flagged = {row['world_id'] for row in read_json(audit_path)['rows']
                   if row.get('audit_status') == 'database_faction_tag_mismatch'}
    rows = []
    for w in worlds:
        rows.append({'world_id': w['world_id'], 'mechanism_id': w['mechanism_id'],
                     'scope': 'actual_catalog' if w['mechanism_id'].startswith('catalog_') else 'research_variant',
                     'native_screened': bool(measured[w['world_id']]),
                     'full_grid_measured': bool(complete[w['world_id']]),
                     'screen_batches': sorted(measured[w['world_id']]),
                     'full_grid_batches': sorted(complete[w['world_id']]),
                     'strict_faction_tag_caveat': w['world_id'] in flagged,
                     'local_independent_analysis_completed': w['world_id'] in confirmed[w['mechanism_id']]['local']})
    write_csv(output / 'A_COVERAGE_WORLDS.csv', rows)
    order = list(dict.fromkeys(w['mechanism_id'] for w in worlds))
    summary = []
    for mechanism in order:
        part = [r for r in rows if r['mechanism_id'] == mechanism]
        summary.append({'mechanism_id': mechanism, 'label': LABELS.get(mechanism, mechanism),
                        'registered': len(part), 'screened': sum(r['native_screened'] for r in part),
                        'full_grid': sum(r['full_grid_measured'] for r in part),
                        'local_confirm': len(confirmed[mechanism]['local']),
                        'heldout_confirm': len(confirmed[mechanism]['heldout']),
                        'claim_status': 'analysis_completed_inspect_conditions' if confirmed[mechanism]['local']
                                        else 'not_independently_confirmed'})
    write_csv(output / 'A_COVERAGE_SUMMARY.csv', summary)
    columns = ['registered', 'screened', 'full_grid', 'local_confirm', 'heldout_confirm']
    values = np.array([[r[k] for k in columns] for r in summary])
    fig, ax = plt.subplots(figsize=(7.4, 6.1))
    ax.imshow((values > 0).astype(int), aspect='auto', cmap=ListedColormap(['#F1F2F3', '#D5E8F2']), vmin=0, vmax=1)
    for (i, j), value in np.ndenumerate(values):
        ax.text(j, i, str(value), ha='center', va='center', color='#263238' if value else GREY)
    ax.set_xticks(range(5), ['Registered', 'Screened', 'Full grid', 'Confirm\nlocal', 'Confirm\nheld-out'])
    ax.set_yticks(range(len(summary)), [row['label'] for row in summary])
    split = next((i for i, m in enumerate(order) if m.startswith('catalog_')), len(order))
    ax.axhline(split - .5, color='white', lw=4)
    ax.tick_params(length=0, pad=7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title('A  Native coverage: every registered mechanism retained', loc='left', pad=12)
    fig.text(.015, .012, 'Cells count worlds, not discoveries. 0 = no completed worlds in that stage.\n'
             'Top: research stat variants. Bottom: actual catalog. Held-out worlds are additional frozen domains.', fontsize=8)
    fig.tight_layout(rect=(0, .07, 1, 1))
    save(fig, output, 'A_native_coverage',
         'Every registered mechanism is shown, including mechanisms with no independent confirmation. '
         'Screening and complete-grid measurement count actual completed native cells. Completed analysis is '
         'not a declaration that a scientific claim passed. Engine-domain faction caveats remain in the audit CSV.', sources)


def reference_means(claim):
    if claim.get('frozen_paths'):
        return np.array(next(iter(claim['frozen_paths'].values()))['initial']['reference_mean'])
    if claim.get('matched_first'):
        return np.array(next(iter(claim['matched_first']['first_prefixes'].values()))['initial']['reference_mean'])
    raise ValueError('Claim has no stored audited reference means')


def capacity_records(claims, manifest):
    meta = {row['claim_id']: row for row in manifest['claims']}
    records, paths = [], []
    for claim in claims:
        if 'matched_first' not in claim:
            continue
        matched = claim['matched_first']
        family, context = claim['claim_id'].split('__', 1)
        for mode, field, prefix_field in [('retain', 'continuations', 'first_prefixes'),
                                         ('value_only', 'value_only_continuations', 'value_only_first_prefixes')]:
            for first in meta[claim['claim_id']]['first_pair']:
                prefix = matched[prefix_field][first]
                for width, solutions in matched[field][first].items():
                    lo, hi = solutions['lower'], solutions['upper']
                    records.append({'claim_id': claim['claim_id'], 'family': family, 'context': context,
                                    'first': first, 'mode': mode, 'batch_limit': int(width),
                                    'capacity_lower': lo['capacity_lower'], 'capacity_upper': hi['capacity_upper'],
                                    'lower_solver_status': lo['status'], 'upper_solver_status': hi['status'],
                                    'upper_search_complete': hi['graph_search_complete'],
                                    'first_prefix_supported': prefix['prefix_lengths']['lower'] == 1,
                                    'first_prefix_possible': prefix['prefix_lengths']['upper'] == 1,
                                    'equivalence_supported': matched['equivalence_supported'],
                                    'equivalence_possible': matched['equivalence_possible'],
                                    'candidate_domain_size': len(claim['domain']['candidate_ids']),
                                    'partner_domain_size': len(claim['domain']['partner_ids']),
                                    'seed_block_id': claim['seed_block_id']})
                    paths.append({'claim_id': claim['claim_id'], 'first': first, 'mode': mode,
                                  'batch_limit': int(width), 'lower_witness': lo['batches'],
                                  'lower_witness_checks': lo['path_checks'],
                                  'optimistic_upper_graph_path': hi['batches'],
                                  'upper_path_is_true_feasible_witness': False,
                                  'frozen_initial_items': claim['initial_items'],
                                  'first_prefix_checks': prefix})
    return records, paths


def capacity_panel(output, claims, manifest, confirmation):
    rows, paths = capacity_records(claims, manifest)
    if not rows:
        return
    write_csv(output / 'B_CAPACITY_BOUNDS.csv', rows)
    write_json(output / 'B_SOURCE_HISTORY_PATHS.json', paths)
    write_json(output / 'B_MATCHED_FIRST_EQUIVALENCE.json', [
        {'claim_id': c['claim_id'], 'task_order': c['task_order'],
         'reference_mean': reference_means(c).tolist(),
         **{key: c['matched_first'][key] for key in ('alpha', 'match_tolerance', 'directions',
                                                    'equivalence_supported', 'equivalence_possible')}}
        for c in claims if 'matched_first' in c])
    identities = []
    worlds = {w['world_id']: w for w in manifest['worlds']}
    for claim in claims:
        if 'matched_first' not in claim:
            continue
        world = worlds[claim['world_id']]
        for prefix, field in [('a', 'candidates'), ('x', 'partners')]:
            for i, item in enumerate(world[field]):
                identities.append({'claim_id': claim['claim_id'], 'source_alias': f'{prefix}{i:02}' if prefix == 'a' else f'{prefix}{i}',
                                   'item_name': item.get('item_name'), 'native_item_id': item.get('native_base_item_id'),
                                   'native_source_id': item.get('source_id'),
                                   'physics_identity_sha256': item.get('physics_identity_sha256'),
                                   'initial_items': claim['initial_items']})
    write_csv(output / 'B_SOURCE_IDENTITIES.csv', identities)
    families = list(dict.fromkeys(r['family'] for r in rows))
    widths = sorted({r['batch_limit'] for r in rows})
    fig, axes = plt.subplots(len(widths), len(families), figsize=(9, 6.2), squeeze=False, sharey=True)
    for ri, width in enumerate(widths):
        for ci, family in enumerate(families):
            ax = axes[ri, ci]
            selected = [r for r in rows if r['family'] == family and r['batch_limit'] == width]
            groups = list(dict.fromkeys((r['context'], r['first']) for r in selected))
            for gi, (context, first) in enumerate(groups):
                for mode, shift, color, marker in [('retain', -.12, BLUE, 'o'), ('value_only', .12, ORANGE, 's')]:
                    row = next(r for r in selected if r['context'] == context and r['first'] == first and r['mode'] == mode)
                    low, high = row['capacity_lower'], row['capacity_upper']
                    x = gi + shift
                    if low is not None and high is not None:
                        ax.vlines(x, low, high, color=color, linewidth=2)
                        ax.plot(x, low, marker, color=color, markersize=5,
                                markerfacecolor=color if row['first_prefix_supported'] else 'white')
                        ax.plot(x, high, '_', color=color, markersize=9)
                    elif high is not None:
                        ax.plot(x, high, 'v', color=color, markerfacecolor='white')
                        ax.annotate('LB ?', (x, high), xytext=(0, -13), textcoords='offset points', ha='center', fontsize=7)
                    else:
                        ax.text(x, .15, 'unresolved', rotation=90, ha='center', fontsize=7)
                    if not row['first_prefix_possible']:
                        ax.plot(x, 0, 'x', color='black', zorder=5)
            ax.set_xticks(range(len(groups)), [f'{first}\n{context.replace("heldout", "held-out")}' for context, first in groups])
            ax.set_title(f'{SOURCE_LABELS[family]}  |  B = {width}')
            ax.set_ylim(bottom=-.35)
            ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
            ax.grid(axis='y', linewidth=.7)
            if ci == 0:
                ax.set_ylabel('Additional release rounds')
            if len(groups) == 4:
                ax.axvline(1.5, color='#DDE1E4', linewidth=.9)
    handles = [Line2D([0], [0], color=BLUE, marker='o', label='Retain every published source'),
               Line2D([0], [0], color=ORANGE, marker='s', label='Value-only: same physical domain')]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.52, .96), ncol=2, frameon=False, fontsize=8)
    all_matched = all(r['equivalence_supported'] and r['first_prefix_supported'] for r in rows)
    title = ('B  Matched immediate utility, different future capacity' if all_matched
             else 'B  Capacity after a frozen first update')
    fig.suptitle(title, x=.02, ha='left', y=1.015)
    fig.text(.015, .006, 'Dots: supported lower bounds; top ticks: upper bounds. Open dots: first prefix unresolved.\n'
             'a05: Arcanist Gloves; a13: Sorcerer\'s Gloves; a07: Second Wind; x3: Spellbound Tome.\n'
             + ('Capacity excludes the first update. Both task frontiers match within the frozen 0.25% equivalence margin.\n' if all_matched else
                'Capacity excludes the first update. First-prefix and frontier-equivalence conditions must be checked separately.\n') +
             'Complete source identities, release paths, solver status and equivalence checks accompany the figure.', fontsize=7.6)
    fig.tight_layout(rect=(0, .115, 1, .91))
    sources = [confirmation / r['file'] for r in read_json(confirmation / 'SUMMARY.json')['claims'] if 'history' in r['claim_id']]
    save(fig, output, 'B_first_update_capacity',
         'Conditional simultaneous bounds for continuation capacity from each frozen first update. '
         'The lower graph supplies feasible witnesses; completed optimistic upper-graph searches supply upper bounds. '
         'Solver status, first-prefix support, frontier equivalence, complete source history and both bound directions '
         'are exported; capacity separation alone does not establish a matched-first research claim.', sources)


def joint_records(claims, manifest):
    meta = {row['claim_id']: row for row in manifest['claims']}
    rows = []
    for claim in claims:
        if 'joint' not in claim:
            continue
        baseline = reference_means(claim)
        family, context = claim['claim_id'].split('__', 1)
        joint = claim['joint']
        controls = meta[claim['claim_id']].get('joint_negative_controls', [])
        pairs = [('main', meta[claim['claim_id']]['joint_pair'], joint)]
        pairs += [(row['control_id'], controls[i]['joint_pair'], row)
                  for i, row in enumerate(joint.get('negative_controls', []))]
        for role, pair, analysis in pairs:
            if analysis.get('status') != 'evaluated_fixed_policy':
                continue
            for ti, task in enumerate(analysis['task_order']):
                for contrast, interval in analysis['contrasts'].items():
                    rows.append({'claim_id': claim['claim_id'], 'family': family, 'context': context,
                                 'world_id': claim['world_id'], 'pair_role': role, 'pair': '+'.join(pair),
                                 'task_id': task, 'contrast': contrast,
                                 **{k: interval[k][ti] for k in ('mean', 'lower', 'upper')},
                                 **{k + '_percent_old_mean': 100 * interval[k][ti] / baseline[ti]
                                    for k in ('mean', 'lower', 'upper')},
                                 'reference_mean': baseline[ti], 'joint_family_alpha': analysis['alpha'],
                                 'joint_family_size': analysis['family_size'], 'headroom': meta[claim['claim_id']]['headroom'],
                                 'seed_block_id': claim['seed_block_id'], 'evidence_stage': 'independent_confirmation'})
    return rows


def horizontal_interval(ax, row, y, color, marker='o', solid=True):
    mean, low, high = (row[k + '_percent_old_mean'] for k in ('mean', 'lower', 'upper'))
    # Machine-precision zeros remain zeros for plotting only; CSV retains raw values.
    if max(abs(mean), abs(low), abs(high)) < 1e-10:
        mean = low = high = 0.
    ax.plot([low, high], [y, y], color=color, linewidth=1.4)
    ax.plot(mean, y, marker, color=color, markersize=4.4, markerfacecolor=color if solid else 'white')


def joint_panel(output, rows, confirmation):
    selected = [r for r in rows if r['pair_role'] == 'main' and r['contrast'] != 'mixed_interaction']
    if not selected:
        return
    series = [('candidate_alone_cap_margin', 'Primary only', GREY, 'o'),
              ('partner_alone_cap_margin', 'Partner only', '#A38D3F', 'v'),
              ('separable_predicted_cap_margin', 'Additive forecast', BLUE, 's'),
              ('joint_cap_margin', 'Actual joint', ORANGE, 'D')]
    families = list(dict.fromkeys(r['family'] for r in selected))
    fig, axes = plt.subplots(1, len(families), figsize=(9.3, 4.6), squeeze=False)
    cap_safe_transfer = []
    for ax, family in zip(axes[0], families):
        part = [r for r in selected if r['family'] == family]
        groups = list(dict.fromkeys((r['context'], r['task_id']) for r in part))
        for gi, (context, task) in enumerate(groups):
            for si, (contrast, label, color, marker) in enumerate(series):
                row = next(r for r in part if r['context'] == context and r['task_id'] == task and r['contrast'] == contrast)
                horizontal_interval(ax, row, gi + (si - 1.5) * .14, color, marker)
        ax.axvline(0, color='#263238', linewidth=.9)
        ax.set_yticks(range(len(groups)), [f'{task}\n{context.replace("heldout", "held-out")}' for context, task in groups])
        ax.invert_yaxis()
        ax.grid(axis='x', linewidth=.7)
        ax.set_xlabel('Cap margin (% of old-reference mean)')
        ax.set_title(f'{SOURCE_LABELS[family]}\nh = {part[0]["headroom"]:.1%}')
        heldout_joint = [r for r in part if r['context'] == 'heldout' and r['contrast'] == 'joint_cap_margin']
        if heldout_joint and all(r['lower'] > 0 for r in heldout_joint):
            cap_safe_transfer.append(SOURCE_LABELS[family].split(':')[0])
    handles = [Line2D([0], [0], color=c, marker=m, label=name) for _, name, c, m in series]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, .92), ncol=4, frameon=False, fontsize=8)
    fig.suptitle('C  Joint-update screening: prediction and physical outcome', x=.015, ha='left', y=1.015)
    if cap_safe_transfer:
        fig.text(.015, .061, ', '.join(cap_safe_transfer) + ' held-out: the joint configuration is below the cap on every task.',
                 color=GREEN, fontsize=8)
    fig.text(.015, .005, 'Positive margin: below cap. Negative margin: above cap. Bars are predeclared paired simultaneous t intervals.\n'
             'All tasks and both local / held-out domains are retained; pair diagnostics alone do not certify source retention.', fontsize=8)
    fig.tight_layout(rect=(0, .12, 1, .86))
    sources = [confirmation / r['file'] for r in read_json(confirmation / 'SUMMARY.json')['claims'] if 'joint' in r['claim_id']]
    save(fig, output, 'C_joint_cap_comparison',
         'Frozen primary-only, partner-only, separable forecast and actual joint cap contrasts. '
         'All interval limits are read from the completed independent analysis; display units use the observed old '
         'reference mean. Local and held-out task outcomes are both shown without selecting a favorable task.', sources)


def controls_panel(run, output, rows, confirmation):
    selected = [r for r in rows if r['contrast'] == 'mixed_interaction']
    development = not bool(selected)
    sources = []
    if development:
        for filename in ('SELECTED_MECHANISMS.json', 'NEGATIVE_CONTROL_MECHANISMS.json'):
            path = run / 'analysis/deep-joint-mechanism-audit-v1' / filename
            if not path.exists():
                continue
            sources.append(path)
            for case in read_json(path):
                family = 'penetration_joint' if case['world_id'].startswith('resistance') else 'mana_joint'
                pair = '+'.join((case.get('a', case.get('candidate')), case.get('x', case.get('partner'))))
                for task in case['tasks']:
                    selected.append({'family': family, 'context': 'development', 'pair': pair,
                                     'task_id': task['task_id'], 'mean_percent_old_mean': 100 * task['mixed_relative_mean'],
                                     'evidence_stage': 'development_point_estimate', 'iterations': task['iterations'],
                                     'lower_percent_old_mean': None, 'upper_percent_old_mean': None})
    else:
        sources = [confirmation / r['file'] for r in read_json(confirmation / 'SUMMARY.json')['claims'] if 'joint' in r['claim_id']]
    if not selected:
        return
    write_csv(output / 'D_MECHANISM_CONTROLS.csv', selected)
    families = list(dict.fromkeys(r['family'] for r in selected))
    fig, axes = plt.subplots(1, len(families), figsize=(9.3, 5.4 if not development else 3.7), squeeze=False)
    for ax, family in zip(axes[0], families):
        part = [r for r in selected if r['family'] == family]
        groups = list(dict.fromkeys((r['pair'], r['task_id']) for r in part))
        contexts = list(dict.fromkeys(r['context'] for r in part))
        for gi, (pair, task) in enumerate(groups):
            for ci, context in enumerate(contexts):
                row = next(r for r in part if r['pair'] == pair and r['task_id'] == task and r['context'] == context)
                y = gi + (ci - (len(contexts) - 1) / 2) * .22
                if development:
                    ax.plot(row['mean_percent_old_mean'], y, 'o', color=GREY, markersize=4.5)
                else:
                    horizontal_interval(ax, row, y, BLUE if context == 'local' else ORANGE,
                                        'o' if context == 'local' else 's')
        ax.axvline(0, color='#263238', linewidth=.9)
        ax.set_yticks(range(len(groups)), [f'{pair} / {task}' for pair, task in groups])
        ax.invert_yaxis()
        ax.grid(axis='x', linewidth=.7)
        ax.set_xlabel('Mixed interaction (% of old-reference mean)')
        ax.set_title(SOURCE_LABELS[family])
    if not development:
        fig.legend(handles=[Line2D([0], [0], marker='o', color=BLUE, label='Local'),
                            Line2D([0], [0], marker='s', color=ORANGE, label='Held-out')],
                   loc='upper center', bbox_to_anchor=(.5, .93), ncol=2, frameon=False)
    stage = 'DEVELOPMENT means, N = 4,096' if development else 'Independent confirmation'
    fig.suptitle(f'D  Positive, reverse and near-zero controls  |  {stage}', x=.015, ha='left', y=1.02)
    fig.text(.015, .008, 'Mixed contrast = joint − primary-only − partner-only + old. Zero and reverse outcomes are retained.\n'
             + ('Point estimates only: these selected development outcomes are not confirmation.' if development else
                'Intervals include all prespecified main / control pairs in one family. An interval crossing zero does not prove absence.'), fontsize=8)
    fig.tight_layout(rect=(0, .115, 1, .9 if development else .88))
    save(fig, output, 'D_mechanism_controls',
         'Signed controls for the two joint-update mechanisms, including every declared task and every local/held-out '
         'domain available in completed confirmation. ' + ('This preview uses selected development means only.' if development else
         'Near-zero roundoff is displayed at zero without changing exported numerical estimates or inferential decisions.'), sources)


def wrappers(folder, output, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        # Source-only wrapper; compiling writes outside the repository.
        content = ('% Generated source wrapper; the included panel is a vector PDF.\n'
                   '% Compile with -output-directory set under WOWFS_WORK_ROOT.\n'
                   '\\documentclass[border=3pt]{standalone}\n\\usepackage{graphicx}\n'
                   '\\providecommand{\\FigureRoot}{' + str(output.resolve()) + '}\n'
                   '\\begin{document}\n\\includegraphics{\\FigureRoot/' + name + '.pdf}\n\\end{document}\n')
        (folder / f'{name}.tex').write_text(content)


def render(run, output, confirmation=None, wrapper_dir=None):
    run, output = Path(run), Path(output)
    confirmation = Path(confirmation) if confirmation is not None else None
    if output.exists():
        raise ValueError('Use a new output directory; figures are not overwritten in place')
    output.mkdir(parents=True)
    style()
    claims, manifest = complete_confirmation(confirmation)
    coverage(run, output, claims, manifest, confirmation)
    if claims:
        capacity_panel(output, claims, manifest, confirmation)
        rows = joint_records(claims, manifest)
        write_csv(output / 'C_JOINT_CONTRASTS_ALL.csv', rows)
        joint_panel(output, rows, confirmation)
    else:
        rows = []
    controls_panel(run, output, rows, confirmation)
    names = sorted(path.stem for path in output.glob('*.pdf'))
    if wrapper_dir is not None:
        wrappers(Path(wrapper_dir), output, names)
    summary = {'status': 'completed', 'evidence_stage': 'independent_confirmation' if claims else 'development_preview',
               'panels': names, 'confirmation_results': str(confirmation) if claims else 'not_run_or_not_complete',
               'scope': 'Figures preserve all selected domains/tasks/controls. No native executions, CI reselection or missing-value imputation.',
               'source_sha256': sha256(__file__), 'outputs': [str(path.resolve()) for path in sorted(output.iterdir())]}
    write_json(output / 'FIGURES_MANIFEST.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--confirmation')
    parser.add_argument('--wrapper-dir')
    args = parser.parse_args()
    print(json.dumps(render(args.run_root, args.output, args.confirmation, args.wrapper_dir), indent=2))


if __name__ == '__main__':
    main()
