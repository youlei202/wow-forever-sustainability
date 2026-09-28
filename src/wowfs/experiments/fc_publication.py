"""Deterministic scientific figures and manuscript tables from completed data."""
import csv
import json
from pathlib import Path
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json

REGIMES=['large_gap','dense','weaker_direct','fixed_budget']
LABELS=['Large gap','Dense','Weaker direct','Fixed budget']
COLORS=['#176b8c','#c65737','#52864a','#82589b']


def readcsv(path):
    with path.open() as f:return list(csv.DictReader(f))


def tex(value):
    return str(value).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')


def savefig(fig,out,name):
    fig.savefig(out/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(out/(name+'.png'),dpi=190,bbox_inches='tight')
    plt.close(fig)


def main():
    root=setup_paths();out=root/'artifacts/final-completion-capacity'
    figures=out/'figures';paper=out/'paper';figures.mkdir(exist_ok=True);paper.mkdir(exist_ok=True)
    summary=json.loads((out/'SUMMARY.json').read_text());old=json.loads((out/'OLD_ECOLOGY_ANALYSIS.json').read_text())
    plans=json.loads((out/'FUTURE_SEQUENCE_DESIGN.json').read_text())
    cmap={c['context_id']:c for c in old['contexts']};pmap={c['context_id']:c for c in plans['contexts']}
    affine={c['context_id'] for c in summary['contexts'] if c['confirmation_affinity']}
    interior=[s for s in summary['sequences'] if s['variant']=='interior' and s['status']=='assessed']
    smap={(s['context_id'],s['regime']):s for s in interior}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'ps.fonttype':42})
    representative='Alliance_Human_Warrior';c=cmap[representative];q=c['tasks'].index(c['binding_effective_task'])
    fig,ax=plt.subplots(1,2,figsize=(7,2.5),gridspec_kw={'width_ratios':[1.2,1]})
    for j,name in enumerate(REGIMES[:2]):
        values=np.array(c['regimes'][name]['relative_values'])[:,q]
        vertical=np.full(5,1-j,dtype=float)
        if j==0:vertical[:4]+=np.linspace(-.15,.15,4)
        ax[0].scatter(values,vertical,s=40,color=COLORS[j],zorder=3)
        ax[0].plot([values.min(),values.max()],[1-j]*2,color=COLORS[j],alpha=.3)
    ax[0].set_yticks([1,0],['Large gap','Dense']);ax[0].set_ylim(-.6,1.6)
    ax[0].set_xlabel('Old task value / shared old optimum');ax[0].set_title('Identical current optimum, 5 partners')
    ax[0].axvline(1,color='gray',ls=':',lw=1)
    ax[0].text(.956,1.3,'4 close partners',fontsize=7)
    for i,regime in enumerate(REGIMES):
        s=smap[representative,regime]
        ax[1].bar(i,s['confirmed_prefix'],color=COLORS[i],width=.65)
        ax[1].plot(i,s['conditional_upper'],marker='_',ms=19,mew=2,color='#222')
    ax[1].set_xticks(range(4),['Gap','Dense','Direct','Budget']);ax[1].set_ylim(0,6.5)
    ax[1].set_ylabel('Updates');ax[1].set_title('Supported path / frozen model upper')
    ax[1].text(.02,.97,'bars: supported lower bounds\nblack marks: conditional predictions',transform=ax[1].transAxes,va='top',fontsize=7)
    fig.tight_layout();savefig(fig,figures,'figure1_same_today')

    fig,ax=plt.subplots(figsize=(5.2,2.8))
    x=np.linspace(0,6,1201)
    for h,color in [(2,COLORS[1]),(5,COLORS[0])]:
        y=np.minimum(h,np.ceil(x-1e-12));ax.step(x,y,where='post',label=f'headroom / gain = {h}',color=color)
    ax.set(xlabel=r'Largest accessible open-band width / gain ($\Delta/g$)',ylabel='Exact scalar capacity',ylim=(-.1,5.4),xlim=(0,6))
    ax.set_yticks(range(6));ax.legend(frameon=False,loc='lower right');ax.set_title('Open-band theorem; abstract, not native observations')
    fig.tight_layout();savefig(fig,figures,'figure2_exact_theory')

    fig,ax=plt.subplots(figsize=(5.2,2.8))
    for name,label,color in zip(REGIMES,LABELS,COLORS):
        rows=sorted([r for r in summary['rounds'] if r['context_id']==representative and r['sequence']==name+'_interior'],key=lambda r:r['round'])
        y=[1]+[float(np.max(np.asarray(r['frontier'])/r['fixed_reference_scale'])) for r in rows]
        ax.plot(range(len(y)),y,marker='o',ms=4,label=label,color=color)
    ax.axhline(1.05,color='#555',ls='--',lw=1);ax.text(.1,1.0505,'fixed cap',fontsize=8)
    ax.set(xlabel='Update index',ylabel='Maximum normalized task frontier',ylim=(.998,1.054),xticks=range(5))
    ax.legend(frameon=False,ncol=2,fontsize=8,loc='lower right');fig.tight_layout();savefig(fig,figures,'figure3_trajectories')

    order=sorted(cmap,key=lambda cid:(cmap[cid]['faction'],cmap[cid]['class'],cmap[cid]['race_label']))
    matrix=np.full((56,8),np.nan)
    for i,cid in enumerate(order):
        for j,regime in enumerate(REGIMES):
            s=smap[cid,regime];matrix[i,j]=s['empirical_prefix'];matrix[i,j+4]=s['confirmed_prefix']
    fig,ax=plt.subplots(figsize=(8.5,12.8));im=ax.imshow(matrix,vmin=0,vmax=5,cmap='YlGnBu',aspect='auto')
    labels=[cmap[cid]['faction'][0]+' '+cmap[cid]['race_label']+' '+cmap[cid]['class']+(' *' if cmap[cid]['native_racial_incomplete'] else '')+(' [nonlinear]' if cid not in affine else '') for cid in order]
    ax.set_yticks(range(56),labels,fontsize=7);ax.set_xticks(range(8),['Gap\nmean','Dense\nmean','Direct\nmean','Budget\nmean','Gap\nLCB','Dense\nLCB','Direct\nLCB','Budget\nLCB'],fontsize=8)
    for i in range(56):
        for j in range(8):ax.text(j,i,str(int(matrix[i,j])),ha='center',va='center',fontsize=7,color='white' if matrix[i,j]>=4 else '#222')
    ax.axvline(3.5,color='#222',lw=1.5);ax.axhline(27.5,color='#222',lw=1.5)
    ax.set_title('All 56 contexts: achieved guarded paths and supported lower bounds\n0 LCB means no certified prefix; it is not a zero-capacity theorem',fontsize=10,pad=12)
    fig.colorbar(im,ax=ax,shrink=.25,pad=.02,label='Successful path prefix (updates)')
    fig.text(.02,.004,'* Known racial omission. Nonlinear: no scalar upper bound. Each LCB uses within-context approximate simultaneous inference.',fontsize=8)
    fig.tight_layout(rect=(0,.015,1,1));savefig(fig,figures,'figure4_full56')

    coverage_rows=readcsv(out/'RACE_CLASS_56_RESULTS.csv')
    for row in coverage_rows:
        cid=row['context_id'];oldrow=cmap[cid]
        row['completion_gap_large_max_task']=max(oldrow['regimes']['large_gap']['max_consecutive_response_gap_by_task'])
        row['completion_gap_dense_max_task']=max(oldrow['regimes']['dense']['max_consecutive_response_gap_by_task'])
        row['native_scalar_mapping_confirmed']=cid in affine
        row['completion_gap_scope']='scalar-compatible' if cid in affine else 'task-vector analogue; no exact scalar theorem'
        row['legacy_mass_all_guarded_rounds']=min(smap[cid,r]['minimum_legacy_mass'] for r in REGIMES)
        row['K_guarded_max']=max(smap[cid,r]['K'] for r in REGIMES)
    with (out/'RACE_CLASS_56_RESULTS.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=coverage_rows[0]);writer.writeheader();writer.writerows(coverage_rows)
    cr={r['context_id']:r for r in coverage_rows};z=np.full((56,9),np.nan)
    for i,cid in enumerate(order):
        z[i,0]=float(cr[cid]['completion_gap_large_max_task'])/.01
        z[i,1]=smap[cid,'large_gap']['conditional_upper'] if cid in affine else np.nan
        z[i,2]=smap[cid,'dense']['conditional_upper'] if cid in affine else np.nan
        z[i,3:7]=[smap[cid,r]['confirmed_prefix'] for r in REGIMES]
        z[i,7]=cr[cid]['legacy_mass_all_guarded_rounds'];z[i,8]=cr[cid]['K_guarded_max']
    visual=z.copy();visual[:,7]*=5
    fig,ax=plt.subplots(figsize=(9,12.8));palette=plt.colormaps['YlGnBu'].copy();palette.set_bad('#dedede')
    ax.imshow(visual,vmin=0,vmax=5,cmap=palette,aspect='auto')
    ax.set_yticks(range(56),labels,fontsize=7)
    ax.set_xticks(range(9),['Gap/g','Pred.\ngap','Pred.\ndense','Gap\nLCB','Dense\nLCB','Direct\nLCB','Budget\nLCB','Legacy\nmass','K'],fontsize=8)
    for i in range(56):
        for j in range(9):
            text=f'{z[i,j]:.2f}' if j==0 else f'{z[i,j]:.2g}' if np.isfinite(z[i,j]) else 'NA'
            ax.text(j,i,text,ha='center',va='center',fontsize=6.8,color='white' if visual[i,j]>=3.7 else '#222')
    for v in [2.5,6.5]:ax.axvline(v,color='#222',lw=1.2)
    ax.axhline(27.5,color='#222',lw=1.2)
    ax.set_title('Completion spectrum, conditional predictions, supported paths, relevance and complexity\nPredictions unavailable for nonlinear Warlocks; all 56 contexts were executed',fontsize=10,pad=12)
    fig.text(.02,.005,'* Racial omission. Legacy mass is the minimum over guarded attempted rounds and all sources; K is the maximum exact mean portfolio size.',fontsize=8)
    fig.tight_layout(rect=(0,.015,1,1));savefig(fig,figures,'figure5_coverage_metrics')

    # A compact main-text view preserves all nine class denominators.
    class_names=['Warrior','Rogue','Hunter','Mage','Warlock','Priest','Paladin','Shaman','Druid']
    fig,axes=plt.subplots(1,2,figsize=(7,3.25),sharey=True)
    for ax,faction in zip(axes,['Alliance','Horde']):
        z=np.full((9,4),np.nan)
        for i,cls in enumerate(class_names):
            for j,regime in enumerate(REGIMES):
                rows=[s for s in interior if s['class']==cls and s['faction']==faction and s['regime']==regime]
                if rows:z[i,j]=np.mean([s['confirmed_prefix'] for s in rows])
        ax.imshow(z,vmin=0,vmax=4,cmap='YlGnBu',aspect='auto')
        for i in range(9):
            for j in range(4):ax.text(j,i,f'{z[i,j]:.2g}' if np.isfinite(z[i,j]) else 'NR',ha='center',va='center',fontsize=8,color='white' if z[i,j]>=3.4 else '#222')
        ax.set_xticks(range(4),['Gap','Dense','Direct','Budget']);ax.set_yticks(range(9),class_names);ax.set_title(faction)
    fig.suptitle('Supported path lower bounds, averaged within each class',fontsize=10);fig.tight_layout();savefig(fig,figures,'figure4_classes')

    # Manuscript rows use class-equal weighting, including executed non-affine
    # Warlocks in observed columns. Predictions have a distinct denominator.
    faction_rows=[]
    for regime in REGIMES:
        row={'regime':regime}
        for faction in ['Alliance','Horde']:
            values=[];bounds=[];preds=[];legacy=[];ks=[]
            for cls in class_names:
                group=[s for s in interior if s['faction']==faction and s['class']==cls and s['regime']==regime]
                if not group:continue
                values.append(np.mean([s['empirical_prefix'] for s in group]));bounds.append(np.mean([s['confirmed_prefix'] for s in group]))
                legacy.append(np.mean([s['minimum_legacy_mass'] for s in group]));ks.append(np.mean([s['K'] for s in group]))
                pred=[s['conditional_upper'] for s in group if s['conditional_upper'] is not None]
                if pred:preds.append(np.mean(pred))
            row.update({faction+'_predicted_8classes':float(np.mean(preds)),faction+'_mean_9classes':float(np.mean(values)),
                        faction+'_supported_lower_9classes':float(np.mean(bounds)),faction+'_legacy_9classes':float(np.mean(legacy)),faction+'_K_9classes':float(np.mean(ks))})
        faction_rows.append(row)
    with (out/'FACTION_MAIN_TABLE.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=faction_rows[0]);writer.writeheader();writer.writerows(faction_rows)
    table=r'''\begin{table*}[t]
\centering\small
\caption{Faction-context robustness of sustainable expansion granularity. Each faction column first averages races within class. Predicted bounds average eight affine classes; observed mean and supported lower prefixes include all nine executed classes (28 contexts per faction). These are averages of bounded paths, not faction strength or population capacities.}
\label{tab:fc-faction}
\begin{tabular}{lrrrrrrrrrr}\toprule
 & \multicolumn{5}{c}{Alliance} & \multicolumn{5}{c}{Horde}\\
Regime & Pred. & Mean & Lower & Legacy & $K$ & Pred. & Mean & Lower & Legacy & $K$\\\midrule
'''
    for label,row in zip(LABELS,faction_rows):
        vals=[row[faction+'_'+key] for faction in ['Alliance','Horde'] for key in ['predicted_8classes','mean_9classes','supported_lower_9classes','legacy_9classes','K_9classes']]
        table+=label+' & '+' & '.join(f'{v:.2f}' for v in vals)+r'\\'+'\n'
    table+=r'\bottomrule\end{tabular}\end{table*}'+'\n';(paper/'fc_faction_table.tex').write_text(table)
    class_table=r'\begin{tabular}{lrrrrll}\toprule Class & A & H & Affine & Total & Supported path (A/H) & Joint D\\\midrule'+'\n'
    for cls in class_names:
        cs=[c for c in old['contexts'] if c['class']==cls];na=sum(c['faction']=='Alliance' for c in cs);nh=len(cs)-na
        ca=sum(c['context_id'] in affine for c in cs)
        label='4/1/4/3 both' if cls!='Warlock' else '0/1/0/1; 0/.67/0/1'
        class_table+=f'{cls} & {na} & {nh} & {ca} & {len(cs)} & {label} & '+('fails (mean)' if cls=='Warrior' else 'unassessed')+r'\\'+'\n'
    class_table+=r'\bottomrule\end{tabular}'+'\n';(paper/'fc_class_table.tex').write_text(class_table)
    mechanism=readcsv(out/'MECHANISM_DIVERSITY.csv')
    mt=r'\begin{tabular}{llrrll}\toprule Family & Context & Pred. gap & Pred. dense & Native mean & Prospective\\\midrule'+'\n'
    aliases={'warrior_weapon_speed':'Weapon speed','mage_mana_regeneration':'Mana regen.','rogue_periodic_proc_rate':'Periodic proc'}
    for row in mechanism:
        context=row['context_id'].split('_')[1]
        mt+=f"{aliases[row['family']]} & {context} & {row['predicted_gap_T']} & {row['predicted_dense_T']} & {row['native_gap_T']}/{row['native_dense_T']} & {row['gap_prospective_prefix']}/{row['dense_prospective_prefix']}"+r'\\'+'\n'
    mt+=r'\bottomrule\end{tabular}'+'\n';(paper/'fc_mechanism_table.tex').write_text(mt)
    atomic_json(out/'PUBLICATION_DATA.json',{'affine_contexts':len(affine),'classes_executed':len(class_names),
        'faction_main_rows':faction_rows,'representative_context':representative,
        'figures':['figure1_same_today','figure2_exact_theory','figure3_trajectories','figure4_classes','figure4_full56','figure5_coverage_metrics']})
    for source in [SOURCE_ROOT/'paper/fc_main.tex',SOURCE_ROOT/'paper/fc_references.bib']:
        shutil.copy2(source,paper/source.name)
    shutil.copytree(SOURCE_ROOT/'paper/fc_sections',paper/'fc_sections',dirs_exist_ok=True)
    print(json.dumps({'figures':6,'native_contexts':56,'affine_contexts':len(affine)}))


if __name__=='__main__':main()
