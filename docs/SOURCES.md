# Verified external sources

Observed on 2026-09-24. Source facts and research choices are separate: the
attached brief defines the experiment design; the pages below only establish
submission requirements and legal character combinations.

| Source | Direct official URL | Observation |
|---|---|---|
| AISTATS 2027 CFP | https://virtual.aistats.org/Conferences/2027/CallForPapers | HTTP 200; deadlines, format, anonymous review, author freeze, and AI disclosure available. |
| AISTATS 2027 FAQ | https://virtual.aistats.org/Conferences/2027/SubmissionFAQ | HTTP 200; cross-check of deadlines, limits, author changes, and disclosure. |
| Official PaperPack | https://aistats.org/aistats2027/AISTATS2027PaperPack.zip | HTTP 200; validated ZIP, 182949 bytes; contains aistats2027.sty, fancyhdr.sty, and sample TeX/PDF. |
| Blizzard character matrix | https://news.blizzard.com/en-us/article/24304075/create-the-hero-you-want-to-be-in-world-of-warcraft-forever | HTTP 200; both matrix tables match the brief, with 28 combinations per faction and nine classes. |

The browser could not render the ZIP, but a direct HTTPS download succeeded and
Python's ZIP validation passed. The download was not replaced with an older
conference style. Its SHA256 is
`aac31ecf2e41f5a2b7f21d00094bfc2fc1207c34d9f955e991b66f3dc98fdb9b`.
The archive and unpacked files live under `WORK_ROOT/external/`; the exact
download record is `WORK_ROOT/provenance/aistats_template.json`.

Both Blizzard table rows use the label Skyborne. Their faction-specific names
come from the headings on the same page: High Order Skyborne and Windshaper
Skyborne. `configs/official_contexts.yaml` preserves them as separate variants.
The page describes updated racial abilities; legality verification does not
validate simulator physics, cooldowns, or implementation. No engine capability
is inferred from these tables.

The saved HTML tables were also parsed and compared entry by entry with the
configuration. Every marked class matched after the documented Skyborne aliases;
`WORK_ROOT/provenance/context_matrix_verification.json` records the two input
hashes and the 28/28 comparison. The stable expanded IDs use faction, race, and
class. Role/spec are separate configuration fields, and no spec is selected yet.

HTML snapshots live under `WORK_ROOT/inputs/`, and URL, HTTP status, snapshot
paths, and SHA256 records are in `WORK_ROOT/provenance/official_sources.json`.
This provenance preserves what was checked without treating a live page as a
version-pinned simulator ruleset. The publication date was not independently
inferred from page layout.

For compilation, Tectonic 0.17.0 was acquired from the
[official release](https://github.com/tectonic-typesetting/tectonic/releases/tag/tectonic%400.17.0).
Its binary, dependencies, and cache remain under `WORK_ROOT`; the archive hash
and download URL are recorded in `WORK_ROOT/provenance/tectonic.json`.
`bash scripts/build_paper.sh` compiles using that binary and the external official
style; TeX intermediates go to `WORK_ROOT/tmp/paper`, the build log to
`WORK_ROOT/logs/paper-build.log`, and the resulting PDF to
`WORK_ROOT/artifacts/latest/paper/main.pdf`. `WOWFS_TECTONIC` and
`WOWFS_PAPERPACK` can override the two dependency locations.

Theoretical references and the scope of prior results are documented separately
in `docs/RELATED_WORK.md` and `paper/references.bib`.
