# Finite reference and conditional native upper bounds

Both analyses read the frozen `capacity-confirmation-v1` data and execute zero new native battles. Source: `src/wowfs/experiments/fc_finite_reference.py`. Results: `SMALL_DOMAIN_ORACLE.csv/.json` and `CAPACITY_UPPER_BOUND_CERTIFICATES.csv/.json` in the final-completion-capacity artifact directory.

## Exact finite reference

For each context and regime, the reference includes the union of the prospective exact and interior primary amplitudes (3–9 candidates), all five old partners, and the original frozen admission mask for each primary. The old five configurations remain admitted. The dynamic program enumerates every reachable primary subset and release order, including decreasing amplitude orders. At each transition it checks complete-library reoptimized gain, power, every old and released source's relevance, and exact finite portfolio coverage. This is P/N/L/H/C/G; it does not impose D.

All 204 affine context-by-regime initial states pass the value/legacy conditions. The exact finite capacities computed from independent fresh means are:

| Regime | Exact finite P/N/L/H/C/G capacity | Contexts |
| --- | ---: | ---: |
| Large gap | 4 | 51 |
| Dense | 1 | 51 |
| Weaker direct | 4 | 51 |
| Fixed budget | 4 | 33 |
| Fixed budget | 3 | 18 |

The utility-only finite oracle equals the value/legacy oracle in every assessed case. The five nonaffine contexts contribute 20 `not_run_nonaffine_exact_domain` records because their full exact candidate domain was not executed. None is assigned zero capacity.

These are exact optimizations of the specified finite, mean-response table, not continuous capacity estimates or confidence-certified sequences. They can differ from the old-fit continuous prediction or the prospective path's passing prefix. Physically executed configurations use direct responses; other configurations use the independently checked per-seed affine interpolation. A generic representation with identical amplitude features, identical external power admission, and the same fixed compatibility row represents exactly the same mask. This comparison does not optimize arbitrary generic weights or establish an algorithmic advantage.

## Conditional continuous dense upper bound

Write `S_q` for the expected utility of the preregistered strongest old configuration, and `C_q=U_high,q-U_zero,q` for the response to a 0.148-unit primary increment. Under the common positive affine response model, let `r=max_q C_q/(0.148 S_q)`. A one-task gain suffices because each of the eight tasks has mass 0.125. Dense completion gaps are `0.011 r`; the strong-family minimum direct increment is `0.0502 r`.

The upper-bound result requires the complete cross-product under one fixed total-contribution cutoff, with all crosses below that cutoff admitted. The frozen power-only masks have this form. It does not apply to the additional asymmetric compatibility budget, whose purpose is to change these completion intervals. Under this condition, every non-direct attainable-value branch has width at most `0.011 r`; the direct branch starts no earlier than `1+0.0502 r`. Therefore `0.011 r <= 0.02` and `0.0502 r > 0.03` imply capacity at most two for headroom 0.05 and gain 0.01. Restricting the amplitude range can only remove attainable branches under the same cutoff.

This analysis reuses the existing simultaneous paired-t contrast family and its critical value within each context. Let `A=C-0.01S` and `B=-0.01S`; both are already members of that family. The two required threshold margins are positive linear combinations:

```
0.011 C/0.148 - 0.02 S = (0.011/0.148) A + (2-0.011/0.148) B
0.0502 C/0.148 - 0.03 S = (0.0502/0.148) A + (3-0.0502/0.148) B
```

The first upper bound is negative on every task; the second lower bound is positive on at least one task, in all 51 affine contexts. Positive slopes and positive old-reference means also pass their derived lower bounds. Across these contexts, the least favorable task gap upper margin is -0.55058 DPS; the smallest context's best direct-increment lower margin is +2.02808 DPS. No additional alpha allocation is used.

Thus all 51 receive a conditional continuous dense utility upper bound of two; the other five are `not_applicable_nonaffine`. This is approximate 95% simultaneous coverage **within each context**, not simultaneous coverage across all 56 contexts. It remains conditional on the affine response and common-cutoff assumptions throughout the declared parameter domain: finite checkpoint agreement does not prove a global physical identity. The result implies the same upper bound for the stricter value/legacy objective and supplies no behavioral-D guarantee.

## Independent behavior and analysis checks

The original Warrior seven-coordinate interpolation audit covers all 1,856 executed checkpoints in ten Warrior contexts and eight tasks. Maximum unnormalized damage-channel residual is `5.684e-13`; maximum rage/resource numerator residual is `1.776e-15`, below the fixed `1e-8` tolerance. This establishes finite checkpoint agreement, not a population novelty bound.

Regression tests verify the exact threshold-combination algebra, rejection of a genuinely wider-gap case, and a two-step feasible release order whose primary amplitude decreases. The separate mechanism sensitivity implementation was also read independently: its paired covariance signs and max/min bounds are valid. Its post-confirmation old-reference sensitivity remains distinct from the original frozen numeric-cap estimand; it reports no fully supported prospective P/G/N/L prefix.
