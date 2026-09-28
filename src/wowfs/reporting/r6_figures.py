"""Standalone publication figures for R6, including the failed cascade probe."""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wowfs.paths import setup_paths


def main():
    root=setup_paths();out=root/'artifacts/r6-theory-native';figs=out/'figures';figs.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'ps.fonttype':42,'savefig.bbox':'tight'})
    def save(fig,name):
        for suffix in ['png','pdf','svg']: fig.savefig(figs/(name+'.'+suffix),dpi=220)
        plt.close(fig)
    records=list(csv.DictReader((out/'CASCADE_INSTANCES.csv').open()))
    hands=[14551,21998,21278,19143];legs=[22385,22000,15057]
    table=np.array([[next(float(r['dps_mean']) for r in records if int(r['glove_id'])==g and int(r['leg_id'])==l and r['condition']=='native') for l in legs] for g in hands])
    a=json.loads((out/'CASCADE_ANALYSIS.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(9,3.6),gridspec_kw={'width_ratios':[1.5,1]})
    im=axes[0].imshow(table,cmap='Blues',vmin=160,vmax=177)
    axes[0].set_xticks(range(3),['Old legs','Heroism repair','Storm repair'])
    axes[0].set_yticks(range(4),['Old anchor','Heroism source','Storm source','Proposed core'])
    for (i,j),value in np.ndenumerate(table): axes[0].text(j,i,f'{value:.2f}',ha='center',va='center',color='white' if value>171 else 'black')
    axes[0].set_title('All 12 legal configurations: mean DPS')
    fig.colorbar(im,ax=axes[0],fraction=.045,pad=.03)
    gates=a['gate_effects'];mean=[r['estimate'] for r in gates]
    axes[1].bar(range(2),mean,color=['#287b8e','#e19138'])
    axes[1].errorbar(range(2),mean,yerr=[[r['estimate']-r['ci_low'] for r in gates],[r['ci_high']-r['estimate'] for r in gates]],fmt='none',color='black',capsize=4)
    axes[1].set_xticks(range(2),['Heroism 4pc','Storm 4pc']);axes[1].set_ylabel('DPS gain over same-gear set-off control')
    axes[1].set_title('Real gates; insufficient repairs')
    fig.suptitle('A: native gate probe did not instantiate the repair-cascade theorem',y=1.06)
    fig.tight_layout();save(fig,'figure1_native_gate_boundary')
    b=json.loads((out/'FRONTIER_NEUTRAL_POLYTOPE.json').read_text())
    c=json.loads((out/'FROZEN_CAPACITY_DESIGN.json').read_text())
    precision=json.loads((out/'CAPACITY_PRECISION_CONFIRMATION.json').read_text())
    panel=next(p for p in c['panels'] if p['delta']==.05)
    vertices=np.array(b['vertices']);line=np.array(b['segment']);points=np.array([d['theta'] for d in panel['designs']])
    fig,ax=plt.subplots(figsize=(6.5,4.3))
    ax.fill(vertices[:,0],vertices[:,1],color='#c6e6e8',alpha=.85,label='Useful region below old frontier')
    ax.plot(line[:,0],line[:,1],color='#287b8e',lw=2,label='Frozen 97.5% utility segment')
    ax.scatter(points[:,0],points[:,1],color='#d5782e',s=45,zorder=3,label=r'Frozen capacity sequence ($\delta=0.05$)')
    ax.scatter(*b['old_theta'],marker='*',color='#202c46',s=140,label='Old research anchor')
    for i,point in enumerate(points,1):ax.annotate(str(i),point,xytext=(5,6),textcoords='offset points')
    ax.set(xlabel='Main-hand physical weapon DPS parameter',ylabel='Native periodic damage per tick',xlim=(-3,190),ylim=(-20,510),title='B: a frontier-neutral native design region')
    ax.legend(fontsize=8,loc='upper right');fig.tight_layout();save(fig,'figure2_neutral_region')
    selected=next(p for p in precision['panels'] if p['delta']==.05)
    rows=selected['rows'];x=np.arange(1,len(rows)+1)
    fig,axes=plt.subplots(1,3,figsize=(11,3.5))
    axes[0].plot(x,[r['point_current_frontier'] for r in rows],'o-',color='#202c46',label='Retained old frontier')
    axes[0].plot(x,[r['mean_DPS'] for r in rows],'s-',color='#287b8e',label='New design mean')
    axes[0].axhline(selected['old_mean_DPS']-b['epsilon_raw'],color='#999999',ls=':',label='Usefulness threshold')
    axes[0].set(ylabel='DPS',title='Fixed frontier; useful new designs');axes[0].legend(fontsize=8,loc='best')
    axes[1].step(np.r_[0,x],np.arange(len(rows)+1)+1,where='post',color='#287b8e',lw=2)
    axes[1].scatter(np.r_[0,x],np.arange(len(rows)+1)+1,color='#287b8e')
    axes[1].set(ylabel='Useful distinct design choices',title='All earlier choices remain useful',yticks=range(1,7))
    axes[2].plot(x,[r['min_full_archive_distance_lower'] for r in rows],'o-',color='#d5782e',label='Simultaneous lower bound')
    axes[2].axhline(.05,color='#202c46',ls='--',label=r'$\delta=0.05$')
    axes[2].set(ylabel='Distance to full prior archive',title='Observable damage-channel novelty');axes[2].legend(fontsize=8)
    for ax in axes:ax.set_xlabel('Accepted update');ax.set_xticks(range(0 if ax is axes[1] else 1,6))
    fig.suptitle('C: five confirmed updates; K = 1 and a fixed six-inequality admission branch',y=1.05)
    fig.tight_layout();save(fig,'figure3_repeatable_expansion')
    summary=precision['summary'];xx=np.arange(len(summary));fig,ax=plt.subplots(figsize=(7,4))
    ax.bar(xx-.18,[r['theorem_guaranteed'] for r in summary],.36,color='#b5c5d7',label='R5 conservative lower bound')
    ax.bar(xx+.18,[r['confirmed_prefix'] for r in summary],.36,color='#287b8e',label='Fresh native sequence confirmed')
    for i,r in enumerate(summary):
        ax.text(i-.18,r['theorem_guaranteed']+.12,str(r['theorem_guaranteed']),ha='center')
        ax.text(i+.18,r['confirmed_prefix']+.12,str(r['confirmed_prefix']),ha='center')
    ax.set(xticks=xx,xticklabels=[str(r['delta']) for r in summary],xlabel='Novelty threshold',ylabel='Number of updates',ylim=(0,11.5),title='Same frozen one-dimensional native region')
    ax.legend();fig.tight_layout();save(fig,'figure4_capacity_agreement')
    print(figs)


if __name__=='__main__':main()
