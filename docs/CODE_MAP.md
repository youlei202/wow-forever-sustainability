# Current scientific code map

The reorganization adds explicit entry points and executed notebooks while retaining scientific module paths: archived hashes and old scripts depend on them. Notebook outputs are tracked for direct viewing. Reexecution reads numerical evidence and original asset generators from the locally supplied external frozen bundle; there is no in-repository manuscript source or `paper/` directory.

| Concept | Implementation in src/wowfs/experiments | Check / notebook |
|---|---|---|
| Finite catalogue, physical configurations, response table, history, weights, retention, cap | co_exact.py: Model, Configuration, evaluate, exhaustive | test_co_exact.py, notebook 00 |
| Fixed-final-frontier support deletion | co_reference.py: support_core, core_slow | test_reproducible_core.py: all deletion orders and greatest fixed point |
| Conflicts above frontier and exact completion | co_reference.py: fixed_frontier, compile_interface | Independent subset oracle in test_reproducible_core.py |
| Maximal future target projections and all joint queries | mi_native.py: maximal and exhaustive audit; mi_theory.py: maximal, downclosure, exact_family | notebooks 00/04 |
| Arbitrary downward-closed families and higher-order obstruction | mi_theory.py: construction, exact_family, run | test_mi_theory.py, notebook 04 |
| Simultaneous paired response bounds | co_native_analysis.py: finite_bounds, certify_queries | co_review_check.py: check_bundle, notebook 03 |
| Supported / possible completion families | mi_native.py: compile_event, run; co_certificate_service.py | notebook 04 |
| Druid pairwise YES / triple NO, cap vs retention | mi_druid.py: run | Independent contrast reconstruction, notebook 04 |
| Retention switch | co_native_analysis.py: certify_queries(..., retention=False), model_from_moments(..., retention=False) | Original obligation replay |
| Configurable tolerance | co_native_sensitivity.py: propagate_tolerance | co_review_check.py: verify_secondary |
| Generic exact solver engineering | co_generic.py, co_benchmark*.py, co_query_benchmark.py | Saved timing and decision audit |

`co_projection.py` is task-distribution projection, not maximal projection of future target sets. These have distinct meanings. Use `co_exact.Model` with Fraction inputs for exact finite mathematics; its validator rejects accidental floats. Native confidence analysis uses the paper's floating-point moments and statistical procedure.

The target representation covers the fixed finite measured catalogue. It does not predict arbitrary future components. A possible witness only passes necessary interval conditions, and is not a certified feasible release.

Historical code modules with prefixes r2/r3/r4/r6/value/fc/oe remain for provenance and earlier studies. The manuscript directory has been removed; archived manuscript-relative paths identify files in the external frozen bundle.
