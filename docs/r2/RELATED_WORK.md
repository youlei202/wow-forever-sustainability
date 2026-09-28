# R2: focused primary-source check

Checked 2026-09-24. These three primary publication records were inspected;
this is a narrow assessment of the supplied references, not an exhaustive
novelty search. No assertion that prior work lacks the proposed application
follows from this check.

| Source | Established tool or scope | Consequence for R2 |
|---|---|---|
| Anders Rantzer, *Distributed Control of Positive Systems*, arXiv:1203.0047, revised 2014; *European Journal of Control* 24 (2015), 72–80. [Primary record](https://arxiv.org/abs/1203.0047), [journal DOI](https://doi.org/10.1016/j.ejcon.2015.04.004). | Positive-system analysis and controller synthesis using linear Lyapunov/storage functions, including scalable verification. | Nonnegative resolvent bounds and resource-storage accounting are background. Replacing network components with item effects is not by itself a new theorem. R2 still needs evidence that the chosen local contracts describe real combat and retain useful choices. |
| Tanner Fiez, Lalit Jain, Kevin Jamieson, Lillian Ratliff, *Sequential Experimental Design for Transductive Linear Bandits* (2019). [Primary record](https://arxiv.org/abs/1906.08399). | A measurement set can differ from the target decision set; the paper gives instance-dependent lower bounds and a sequential design algorithm with near-matching guarantees up to logarithmic factors. | Signature probes versus configuration decisions are already a recognized experimental-design distinction. Compare against a method with the same features, measurements and information. Estimating a few parameters instead of independent configuration means is not sufficient statistical novelty. No reproduction of this algorithm is claimed. |
| Nathaniel Budijono, Phoebe Goldman, Jack Maloney, Joseph B. Mueller, Phillip Walker, Jack Ladwig, Richard G. Freedman, *Ludus: An Optimization Framework to Balance Auto Battler Cards*, AAAI 36(11) (2022), 12727–12734. [Publisher record](https://ojs.aaai.org/index.php/AAAI/article/view/21550), [DOI](https://doi.org/10.1609/aaai.v36i11.21550). | Automated playtesting, global search over card parameters, and sampling-based approximation support new-content balancing and metagame objectives. | Simulation, search and new-item balancing are established baseline categories. An R2 comparison may use that category, but must not call a home-built generic optimizer the full Ludus algorithm. A frozen cross-update mechanism with preserved behavioral choices requires its own evidence. |

## Current claim boundary

The one conditional proposition in [THEORY.md](THEORY.md) establishes that
uniform event debit contracts bound every time window, and gives a finite
timing-choice witness with zero task-envelope growth and exact `K=2`. Its
proof uses elementary storage accounting, interval geometry and a coverage
argument. **Originality is not established.** The witness is not a native
finding and is not offered as another abstract benchmark.

The potentially useful research distinction is between a fixed performance
envelope and the set of within-fight behaviors attainable by existing gear
and strategies. New behaviors can be competitive without raising any task
optimum, while having zero scalar performance loss when deleted. Conversely,
if old strategies or the declared randomization model already synthesize
those profiles, apparent behavioral novelty disappears. Native source and
event interventions must decide which case applies.

No claim is made that structured additive rules outperform a same-dimension
generic class containing them. Any future advantage must concern how a valid
structure is obtained, how conservatively it controls native interactions,
or which real reward choices it preserves under matched information and
compute. Those empirical and statistical claims remain open.
