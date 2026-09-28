# Standalone figure compilation

The original PDF and SVG panels are complete vector figures; compiling the
wrapper is optional. Each `.tex` source includes its matching PDF and adds a
small standalone border. It does not recompute data or confidence intervals.

For a portable extracted ZIP, place the four `.tex` files beside the matching
four original `.pdf` files. Run the following **from that directory**. The
explicit `FigureRoot` definition overrides the wrapper's workspace default.
Distinct job names and a separate output directory preserve the original PDFs.

```bash
mkdir -p compiled-wrappers
for panel in A_native_coverage B_first_update_capacity C_joint_cap_comparison D_mechanism_controls
do
  pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape \
    -output-directory=compiled-wrappers \
    -jobname="${panel}_standalone" \
    "\\def\\FigureRoot{.}\\input{${panel}.tex}"
done
```

The backslashes above are ordinary shell-quoted TeX commands, not generated
shell substitutions. Any `pdflatex` installation with the `standalone` and
`graphicx` packages is sufficient. In the research workspace, compile outputs
must stay under `WOWFS_WORK_ROOT`.

All four wrappers were checked with the already present TeX Live 2026 compiler
at `envs/behavioral-texlive/bin/x86_64-linux/pdflatex`. The test also redefined
`FigureRoot` to `.` and used the `_standalone` job-name suffix. It produced four
one-page PDFs, with no package installation or shell escape. Compiler logs and
hash records accompany `compiled-wrappers/COMPILATION.json` in the final figure
artifact directory.
