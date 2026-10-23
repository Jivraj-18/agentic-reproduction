# Agentic reproduction of two Wiley papers

Blind reproduction of one results table from each of two open-access Wiley papers, using only the extracted Methods and the authors' deposited data. Every cell is graded against the published value, and each miss is traced to a root cause.

- **Scorecard:** `docs/index.html` (published as the GitHub Pages site)
- **Write-up, caveats and findings:** `NOTES.md`
- **Pipeline code:** `scripts/` (extraction, sandbox build, grading, audits, report build)
- **Per-paper work:** `work/paperA`, `work/paperB` (first extraction), `work/paperB2` (corrected extraction): extracted Methods, blinded templates, each run's code and assumptions, grades, audits, attributions

The deposited data are not in this repository. Get them from Dryad:
[10.5061/dryad.f3r6799](https://doi.org/10.5061/dryad.f3r6799) (Paper A) and
[10.5061/dryad.0cfxpnwcq](https://doi.org/10.5061/dryad.0cfxpnwcq) (Paper B), and unzip into `work/<paper>/source/data/` to re-run.
