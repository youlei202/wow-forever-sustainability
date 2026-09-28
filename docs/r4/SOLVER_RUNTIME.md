# HiGHS scheduler compatibility fix

The full test suite exposed a runtime interaction between earlier scipy
linprog calls and the R4 MILP thread cap. SciPy1.18.1 embeds HiGHS1.12.0 with
a process-global scheduler. A preceding default linprog initialized128
threads; the later MILP requested one thread and returned status4,
`(HiGHS Status 0: Not Set)`, without solving the model. Isolated R4 tests
passed because they initialized the scheduler themselves.

After all recorded C/E comparisons, the current source added one conditional
retry: only this exact status/message with no incumbent triggers
`_Highs.resetGlobalScheduler(True)`, then the same model and numerical options
are submitted once more. The initial failure is retained in the returned
`runtime_scheduler_retry` record. Other errors and infeasibility results are
not reclassified. Frozen run snapshots and scientific outcomes were not
modified; the change concerns runtime initialization, not the admission MILP.

A regression test deliberately initializes a two-thread linprog scheduler
before solving a known feasible R4 model. The full maintained suite then
passed70/70 tests. Its log is
`WOWFS_WORK_ROOT/artifacts/r4-foundational-discovery/PYTEST_AFTER_SCHEDULER_FIX.log`.
