#!/usr/bin/env python3
"""Render native confirmation/obligation records as standalone vector TeX.

This presentation code does not alter or adjudicate any scientific decision.
Compile the emitted TeX with output-directory under WOWFS_WORK_ROOT.
"""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path


PREAMBLE=r"""\documentclass[tikz,border=3pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{lmodern,pgfplots}
\pgfplotsset{compat=1.18}
\definecolor{gapblue}{HTML}{4477AA}
\definecolor{densered}{HTML}{EE7733}
\definecolor{directgreen}{HTML}{228833}
\definecolor{inkgray}{HTML}{343A40}
\definecolor{gridgray}{HTML}{DEE3E8}
\definecolor{pendinggray}{HTML}{AAB4BE}
\newcommand{\AllianceBadge}{\tikz[baseline=-.4ex,x=.65ex,y=.65ex]{\path[fill=gapblue] (-.7,.9)--(.7,.9)--(.7,-.2)--(0,-.9)--(-.7,-.2)--cycle;}}
\newcommand{\HordeBadge}{\tikz[baseline=-.4ex,x=.65ex,y=.65ex]{\path[fill=densered] (0,1)--(.75,0)--(.45,-.8)--(0,-.45)--(-.45,-.8)--(-.75,0)--cycle;}}
\begin{document}
"""


def tex_escape(text):
    return str(text).replace("_",r"\_").replace("%",r"\%").replace("&",r"\&")


def grid(rows):
    base=[r for r in rows if r["variant"]=="base"]
    worlds=list(dict.fromkeys(r["world_id"] for r in base))
    color={"YES":"directgreen","NO":"densered","UNKNOWN":"pendinggray","UNKNOWN_INITIAL":"pendinggray","INVALID_INITIAL":"inkgray"}
    counts=Counter(r["confidence_status"] for r in base)
    flip=sum(r["prediction_changed_on_fresh_mean"] for r in base)
    parts=[PREAMBLE,r"\begin{tikzpicture}[x=.56cm,y=.36cm,font=\small]",
           r"\node[anchor=west,font=\bfseries] at (-7.6,2.6) {C. Prospective completion decisions in independent catalogues};",
           r"\node[anchor=west,font=\footnotesize] at (-7.6,1.45) {Fixed $N=16{,}384$ per cell; unrestricted helpers; every published source retains a use};"]
    for j in range(8):parts.append(rf"\node at ({j+.4},.35) {{$D_{{{j+1}}}$}};")
    for wi,wid in enumerate(worlds):
        unit=[r for r in base if r["world_id"]==wid]
        first=unit[0];number=int(wid.rsplit("_",1)[-1])+1
        name={"warrior_weapon_skill":"Warrior / weapon", "paladin_seal_twisting":"Paladin / seal",
              "mage_timed_resources":"Mage / timed item", "druid_passive_resources":"Druid / resource"}[first["stratum"]]
        dagger=r"$\dagger$" if number==1 else ""
        label=rf"{name} {number} {dagger} \{first['faction']}Badge\ {first['faction']}"
        y=-wi-.6
        parts.append(rf"\node[anchor=east,font=\footnotesize] at (-.35,{y:.2f}) {{{label}}};")
        for j,row in enumerate(unit):
            fill=color.get(row["confidence_status"],"inkgray")
            parts.append(rf"\fill[{fill}] ({j+.03},{y-.33:.2f}) rectangle ({j+.77},{y+.33:.2f});")
            if row["prediction_changed_on_fresh_mean"]:
                parts.append(rf"\draw[black,very thick] ({j+.24},{y-.17:.2f})--({j+.56},{y+.17:.2f}) ({j+.24},{y+.17:.2f})--({j+.56},{y-.17:.2f});")
        if wi in (3,7,11):parts.append(rf"\draw[gridgray] (-7.6,{y-.52:.2f})--(8,{y-.52:.2f});")
    y=-len(worlds)-1.2
    legends=[("directgreen",f"YES {counts['YES']}"),("densered",f"NO {counts['NO']}"),
             ("pendinggray",f"Unresolved {counts['UNKNOWN']+counts['UNKNOWN_INITIAL']}")]
    for k,(col,label) in enumerate(legends):
        x=-7.4+5*k
        parts.append(rf"\fill[{col}] ({x},{y-.2}) rectangle ({x+.5},{y+.2});\node[anchor=west,font=\footnotesize] at ({x+.7},{y}) {{{label}}};")
    parts.append(rf"\node[anchor=west,font=\footnotesize] at (-7.6,{y-1.1}) {{Cross: prediction / fresh-mean disagreement ({flip}/128). $\dagger$: four tasks.}};")
    parts.append(rf"\node[anchor=west,font=\footnotesize] at (-7.6,{y-2.05}) {{16 registered menus, 8 queries each; approximate simultaneous paired-$t$ family, total $\alpha=.04$.}};")
    parts.extend([r"\end{tikzpicture}",r"\end{document}"])
    return "\n".join(parts)+"\n"


def obligations(rows,expansions,tolerance=None):
    base=[r for r in rows if r["variant"]=="base"]
    sufficient=[sum(r[f"{g}_alone_sufficient"] for r in base) for g in ("legacy","targets","helpers")]
    necessary=[sum(r[f"{g}_necessary_for_obstruction"] for r in base) for g in ("legacy","targets","helpers")]
    retained=sum(r["retention_essential"] for r in base)
    allno=sum(r["all"]=="NO" for r in base)
    flips=Counter((r["base_mean"],r["expanded_mean"]) for r in expansions)
    maxcount=max(sufficient+necessary+[1])
    xmax=max(10,10*((maxcount+9)//10))
    coords=lambda values:" ".join(f"({value},{2-i})" for i,value in enumerate(values))
    parts=[PREAMBLE,r"\begin{tikzpicture}",
       rf"\begin{{axis}}[width=12.3cm,height=6cm,font=\small,xbar,bar width=8pt,xmin=0,xmax={xmax},",
       r"ytick={0,1,2},yticklabels={Published helpers,Required targets $D$,Legacy sources $H$},",
       r"xlabel={Certified query count (128 registered base queries)},",
       r"title={D. Which source obligations cause the obstruction?},title style={font=\small\bfseries},",
       r"ymin=-.6,ymax=2.6,xmajorgrids,grid style={gridgray},axis line style={inkgray},",
       r"legend style={at={(.5,-.26)},anchor=north,draw=none,font=\footnotesize,legend columns=1},",
       r"nodes near coords,point meta=x,every node near coord/.append style={font=\footnotesize},clip=false]",
       rf"\addplot[fill=gapblue,draw=gapblue] coordinates {{{coords(sufficient)}}};",
       r"\addlegendentry{Only this group's retention enforced: NO; value-only completion: YES}",
       rf"\addplot[fill=densered,draw=densered] coordinates {{{coords(necessary)}}};",
       r"\addlegendentry{Dropping this group's retention requirement changes NO to YES}",
       rf"\node[anchor=north,align=center,font=\footnotesize] at (axis description cs:.5,-.54) {{{retained}/{allno} supported NO queries are retention-essential. Labels overlap; no stacking.\\",
       rf"Eight expanded menus / 64 paired targets: mean NO$\to$YES = {flips[('NO','YES')]}; YES$\to$NO = {flips[('YES','NO')]}.\\",
       (rf"At $e=5\%$, {tolerance['thresholds'][-1]['retention_essential_queries']} retention-essential NO remain in {tolerance['thresholds'][-1]['retention_essential_catalogues']} catalogues; additional $\alpha=0$.\\" if tolerance else ""),
       r"\AllianceBadge\ Alliance and \HordeBadge\ Horde: eight registered catalogues each; same finite event.};",
       r"\end{axis}",r"\end{tikzpicture}",r"\end{document}"]
    return "\n".join(parts)+"\n"


def tolerance_panel(summary):
    thresholds=summary["thresholds"]
    labels=[f"{100*float(Fraction(t['tolerance'])):g}" for t in thresholds]
    coordinates=lambda status:" ".join(f"({i},{t['confidence_counts'].get(status,0)})" for i,t in enumerate(thresholds))
    parts=[PREAMBLE,r"\begin{tikzpicture}",
      r"\begin{axis}[width=10.4cm,height=6.5cm,font=\small,ybar stacked,bar width=26pt,",
      r"title={E. Tolerance choice changes most native obstructions},title style={font=\small\bfseries},",
      rf"xtick={{0,1,2,3}},xticklabels={{{','.join(labels)}}},xmin=-.6,xmax=3.6,",
      r"xlabel={Source tolerance $100e$ (\% of original reference)},ylabel={Registered base queries},",
      r"ymin=0,ymax=136,ytick={0,32,64,96,128},ymajorgrids,grid style={gridgray},",
      r"axis line style={inkgray},clip=false,legend style={at={(.5,-.23)},anchor=north,draw=none,legend columns=3,font=\footnotesize}]"]
    for status,color in (("YES","directgreen"),("NO","densered"),("UNKNOWN","pendinggray")):
        parts.extend([rf"\addplot[fill={color},draw={color}] coordinates {{{coordinates(status)}}};",rf"\addlegendentry{{{status if status!='UNKNOWN' else 'Unresolved'}}}"])
    parts.extend([r"\node[anchor=north,align=center,font=\footnotesize] at (axis description cs:.5,-.4)",
      r"{16 catalogues / 128 targets; $h=.10$, $g=.01$, $\rho=\rho_g=.5$.\\",
      rf"{thresholds[-1]['primary_NO_to_supported_YES']}/76 primary NO become YES at $e=5\%$; {thresholds[-1]['retention_essential_queries']} retention-essential obstructions remain.\\",
      r"\AllianceBadge\ Alliance / \HordeBadge\ Horde; same simultaneous event, no new simulations or alpha.};",
      r"\end{axis}",r"\end{tikzpicture}",r"\end{document}"])
    return "\n".join(parts)+"\n"


def expansion_panel(rows,decisions):
    """Every paired target; the two half-cells show base and expanded status."""
    worlds=list(dict.fromkeys(r["world_id"] for r in rows))
    info={r["world_id"]:r for r in decisions}
    colors={"YES":"directgreen","NO":"densered","UNKNOWN":"pendinggray"}
    transitions=Counter((r["base_confidence"],r["expanded_confidence"]) for r in rows)
    means=Counter((r["base_mean"],r["expanded_mean"]) for r in rows)
    parts=[PREAMBLE,r"\begin{tikzpicture}[x=.56cm,y=.48cm,font=\small]",
        r"\node[anchor=west,font=\bfseries] at (-7.6,2.5) {D. Optional candidate expansion: all 64 paired targets};",
        r"\node[anchor=west,font=\footnotesize] at (-7.6,1.6) {$8\!\times\!4$ base menu $\to10\!\times\!5$ expanded menu; same $H,D$, tasks, reference and thresholds};"]
    for j in range(8):parts.append(rf"\node at ({j+.4},.55) {{$D_{{{j+1}}}$}};")
    names={"warrior_weapon_skill":"Warrior / weapon", "paladin_seal_twisting":"Paladin / seal",
           "mage_timed_resources":"Mage / timed item", "druid_passive_resources":"Druid / resource"}
    for wi,wid in enumerate(worlds):
        d=info[wid];number=int(wid.rsplit('_',1)[-1])+1;y=-wi-.4
        label=rf"{names[d['stratum']]} {number} \{d['faction']}Badge\ {d['faction']}"
        parts.append(rf"\node[anchor=east,font=\footnotesize] at (-.35,{y}) {{{label}}};")
        for j,row in enumerate(r for r in rows if r['world_id']==wid):
            for k,key in enumerate(('base_confidence','expanded_confidence')):
                x=j+.03+.38*k
                parts.append(rf"\fill[{colors[row[key]]}] ({x},{y-.29}) rectangle ({x+.35},{y+.29});")
            if row['base_confidence']!=row['expanded_confidence']:
                parts.append(rf"\draw[black,very thick] ({j+.03},{y-.29}) rectangle ({j+.76},{y+.29});")
        if wi%2==1 and wi!=len(worlds)-1:parts.append(rf"\draw[gridgray] (-7.6,{y-.5})--(8,{y-.5});")
    y=-len(worlds)-.6
    for i,(status,color) in enumerate(colors.items()):
        x=-7.4+5*i;count=transitions[(status,status)]
        parts.append(rf"\fill[{color}] ({x},{y-.16}) rectangle ({x+.45},{y+.16});\node[anchor=west,font=\footnotesize] at ({x+.6},{y}) {{{status if status!='UNKNOWN' else 'Unresolved'} $\to$ same: {count}}};")
    parts.extend([rf"\node[anchor=west,font=\footnotesize] at (-7.6,{y-1}) {{Each split cell: base (left), expanded (right). Status transitions: 0/64.}};",
        rf"\node[anchor=west,font=\footnotesize] at (-7.6,{y-1.85}) {{Exact means: {means[('YES','YES')]} YES$\to$YES, {means[('NO','NO')]} NO$\to$NO; no rescue from these registered additions.}};",
        rf"\node[anchor=west,font=\footnotesize] at (-7.6,{y-2.7}) {{Optional additions preserve feasible publications; absent observed benefit does not prove all expansions ineffective.}};",
        r"\end{tikzpicture}",r"\end{document}"])
    return "\n".join(parts)+"\n"


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--confirmation",required=True);p.add_argument("--obligations",required=True);p.add_argument("--source-output",required=True);p.add_argument("--tolerance")
    args=p.parse_args();confirmation=Path(args.confirmation);audit=Path(args.obligations);output=Path(args.source_output)
    output.mkdir(parents=True,exist_ok=True)
    decisions=json.loads((confirmation/"NATIVE_DECISIONS.json").read_text())
    audits=json.loads((audit/"OBLIGATION_DECISIONS.json").read_text())
    expansions=json.loads((confirmation/"CATALOG_EXPANSION_RESULTS.json").read_text())
    (output/"native_C_decisions.tex").write_text(grid(decisions))
    tolerance=json.loads(Path(args.tolerance).read_text()) if args.tolerance else None
    (output/"native_D_obligations.tex").write_text(obligations(audits,expansions,tolerance))
    (output/"native_D_candidate_expansion.tex").write_text(expansion_panel(expansions,decisions))
    if tolerance:(output/"native_E_tolerance.tex").write_text(tolerance_panel(tolerance))


if __name__=="__main__":main()
