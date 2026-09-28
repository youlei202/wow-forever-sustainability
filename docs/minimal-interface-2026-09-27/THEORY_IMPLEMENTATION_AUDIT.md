# Theory and implementation audit — 27 September 2026

The corrected independent checker passes all 2,466 prescribed construction
checks. An initial checker defect caused 716 guarantee-range mismatches; that
failed run, its source, malformed inputs, and diagnosis remain intact. No
counterexample to the supplied theorem was established. These are abstract
finite implementation checks, not native runs or experimental proofs.

## Evidence and independence

The five-page proof note was read in full from
`$WOWFS_WORK_ROOT/inputs/minimal-interface-2026-09-27/WoW_Minimal_Interface_Codex_Handoff/wow_minimal_interface_proof.pdf`.
The extracted text and source hash are in `theory/PROOF_EXTRACTED.txt` and
`theory/PROOF_READ_RECEIPT.json`. The supplied note arrived after the initial
attachment had been transcribed, but before either complete theory run.

`src/wowfs/experiments/mi_theory.py` uses only Python standard-library modules.
It does not import the original checker, the certificate query service, or any
WoW completion solver. At each selected glove set and attainable frontier, it
includes all boots whose column maximum lies within the retention window.
Adding any such boot preserves the frontier bound and boot retention and can
only add glove witnesses. Conversely, every valid publication at this frontier
uses a subset of these boots. Mandatory old items, attainment, gain, every
selected source, and the cap are checked. Thus this finite enumeration is
complete without assuming that its resulting family equals the construction's
requested family.

A separate literal publication-powerset oracle checks containment directly and
does not call the production downclosure helper. Six tests cover all 199
downsets through four targets, 180 arbitrary tables with one to three targets,
perturbed constructions, empty-family behavior, exact boundary examples,
non-prefix submasks, semantic witnesses, and symbolic equivalence.

## Retained failed version and correction

The initial complete run is retained at
`$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27/theory/`.
Its `FAILED_V1_SOURCE.py` is the exact original checker; `FAILED_V1_AUDIT.json`
records the defect and links to the corrected run. The initial submask iterator
used the changing mask in `(mask - 1) & mask`, producing one descending chain
instead of every subset. This affected both random input generation and query
closure. Independent validation found that 179 of the 192 generated random
families were not downsets. Those 179 cases accounted for every one of the
716 mismatches at eta = 0, 0.1, 0.25, and 0.49; the original run also retains
their 358 mismatches outside the guaranteed perturbation range.

The correction preserves the original mask during submask enumeration. The
new regression checks require all eight subsets of mask `0b1011`; the brute
oracle was also made independent of this helper. The theorem, response
construction, seeds, and prescribed cases were not tuned. Correct random
downsets were regenerated under the same seed, with new source hashes, in the
separate `theory/v2/` directory. No previous output was overwritten.

The corrected source SHA-256 is
`5365112d37a3e9af096b151aefd6bbbe72d8dd53da2e1ac174e04a7bd0aa3d96`.
The configuration SHA-256 is
`673e2017d0290ee1348eb0aa62d3a2139124ed9eebef6652c3d3b65de9b9b7b4`.
The original failed output must not be mistaken for the corrected result.

## Universal construction and perturbations

The corrected run includes all 2, 3, 6, 20, and 168 downsets on zero through
four targets, respectively (199 total, including the empty family). It also
includes 64 seeded random downsets at each of five, six, and seven targets,
and 20 high-order instances: a positive/negative pair for every r = 1,...,10.
Each pair uses the same component labels and physical supports, differing only
in the designated target-selector responses; all current-history responses
coincide. Proper subsets agree, and the full r+1 target set distinguishes the
pair. The largest tested minimal obstruction has order 11. This is not native
obstruction-order evidence.

Each of the 411 instances is checked nominally and at eta = 0.1, 0.25, 0.49,
0.50, and 0.51: 411 nominal checks and 2,055 perturbation checks. Each
perturbation uses independent seeded `Random.uniform(-eta, eta)` draws for all
physical responses, rounded to integer nanounits for exact comparison. The
perturbed initial frontier is used when checking gain. One perturbation draw
per eta per instance is used; this is not a probability estimate or a uniform
sample of all downsets. Original tables, seeds, inputs, and response hashes
permit reconstruction.

All 2,466 corrected families equal their intended families. In particular,
all 1,644 checks within the strict guarantee (including unperturbed cases)
pass, including all empty-family cases. The 822 uniform perturbation checks
at eta >= 0.5 also happen to preserve the family; this does not extend the
theorem's guarantee. Separately recorded deterministic corners for the
two-target pair obstruction preserve the family at eta <= 0.49 and make the
forbidden pair feasible at eta = 0.50 and 0.51. At eta = 0.50 the nominal
102 responses become 102.5, the nominal 104 responses become 103.5, and the
old glove is exactly within the retention tolerance of one. These corners are
explicitly labelled as adversarial boundary checks, not uniform draws.

The proof's forward construction, backward old-glove exclusion, empty-family
case, and strict perturbation inequalities were reviewed. Computational checks
support implementation consistency; the supplied mathematical argument, not
these counts, supplies the universal statement.

## Semantic minimality

Two different full-publication interfaces are stored in
`v2/SEMANTIC_MINIMALITY_CHECKS.json`. One uses either `helper_a` or `helper_b`;
the other uses `helper_c`. Both project to the same maximal target `{x0}` in
the two-target universe `{x0,x1}`. All four target queries agree, while the
full helper witnesses differ. This intentionally demonstrates loss of helper
information. Target-only semantics need an extra witness payload to return a
full publication.

The note's factorization argument is sound for a fixed labelled finite target
universe and a decoder with no uncounted instance-specific side information.
It establishes a coarsest exact query invariant, not shortest serialization,
efficient decoding, an adaptive policy state, or bibliographic originality.

## Succinct representation scope guard

The explicit JSON antichain stores lists of target integer IDs. The symbolic
JSON stores the target count and forbidden pairs. Both exact byte strings and
hashes are saved. They share the declared label/decoder convention; interpreter
code is not charged to either serialization. The audited physical construction
has 2p+4 components, all (p+2)^2 crosses, one task, and cap-safe responses.

| p | Explicit maximal sets | Explicit bytes | Pair rules | Symbolic bytes | Queries checked |
|---|---:|---:|---:|---:|---:|
| 4 | 16 | 161 | 4 | 62 | 256 / 256 |
| 8 | 256 | 5,377 | 8 | 93 | 65,536 / 65,536 |
| 12 | 4,096 | 135,169 | 12 | 125 | 14,104 / 16,777,216 |
| 16 | 65,536 | 2,949,121 | 16 | 157 | 75,553 / 4,294,967,296 |

Every checked query agrees. For p=12 and p=16, the query pool contains all
explicit maximal sets, every forbidden pair, empty/full targets, and 10,000
seeded random masks before deduplication. These are not exhaustive query
enumerations. A separate exact structural check verifies all 2^p unique
choices of one endpoint per pair, which establishes the representation
identity: every allowed partial choice extends to one of those maximal sets,
and no maximal set contains a forbidden pair. For accepted tested queries,
the full helper publication is checked against the response table; rejected
queries retain the old-glove contradiction under every helper extension.

The symbolic representation is substantially smaller on these examples. No
timing comparison or storage-optimality claim is made. The proof's counting
lower bound is in target count with all advice charged; it is not an
exponential lower bound in total input size, since the universal construction
may use exponentially many selectors.

## Execution and reproduction

Both full runs used one CPU worker in tmux after sourcing `scripts/env.sh`;
GPU count and native simulations are zero. Checkpoints are written after each
case. Run configurations and checker-source hashes must match on resume.
`v2/RESUME_CHECKS.json` records a successful completed resume and expected
rejections for changed configuration and changed source. A completed run
returns without modifying its data.

From the repository, reproduce in a new empty output directory:

```bash
source scripts/env.sh
python -m pytest -q tests/test_mi_theory.py
python -m wowfs.experiments.mi_theory --out "$WOWFS_WORK_ROOT/artifacts/minimal-interface-theory-reproduction"
```

Use tmux for the full execution and append `--resume` only to continue the
same source/configuration. The maintained source and this audit remain in the
repository; inputs, checkpoints, logs, serialized examples, and retained
failed evidence remain under `WOWFS_WORK_ROOT`. No manuscript was edited.
