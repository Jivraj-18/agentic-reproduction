# Agentic reproduction of two Elsevier papers

Blind reproduction of one results table from each of two open-access Elsevier papers, using only a summary of the Methods and the authors' deposited data. Each table was rebuilt twice, once by Claude Opus 5.5 and once by Claude Sonnet 5.5. Every cell is graded against the published value, and each miss is traced to a cause by re-running the alternative reading.

The publisher's name says whose papers were used. This work is not produced by or for the publisher.

- **Page:** `docs/index.html` (GitHub Pages; same layout as the Wiley page, with an Opus 5.5 / Sonnet 5.5 switch in each paper tab)
- **Write-up, costs and caveats:** `NOTES.md`
- **Pipeline:** `scripts/` (sandbox build, grading, audits, cost, page build); `scripts/EXPLAIN.md` is the explainer's brief
- **Per paper:** `work/paperA`, `work/paperB`: extraction (`extract/`, built by `extract/build_extract.py`), each run's code and assumptions (`sandbox/r_opus`, `sandbox/r_sonnet`), grades, audits, costs and the explainer's tests (`eval/`)

## Papers

- **Paper A:** Labrosse KB, et al. Intracorporeal vs. extracorporeal open and closed knot tying techniques in laparoscopy: A randomized, controlled study. *Heliyon* 2024; 10: e25178. [doi:10.1016/j.heliyon.2024.e25178](https://doi.org/10.1016/j.heliyon.2024.e25178). Data: [Dryad 10.5061/dryad.p2ngf1vvf](https://doi.org/10.5061/dryad.p2ngf1vvf).
- **Paper B:** Dawson DA, Schultz TW Equations for estimating binary mixture toxicity: Methyl-2-chloroacetoacetate-containing combinations. *Toxicology Reports* 2025; 14: 101939. [doi:10.1016/j.toxrep.2025.101939](https://doi.org/10.1016/j.toxrep.2025.101939). Data: [OSF osf.io/ysxrb](https://osf.io/ysxrb).

The deposited data are not in this repository (the CC BY papers are, under `work/<paper>/source/`). Download the data from the links above into `work/<paper>/source/data/` to re-run. Rebuild the page with:

```
python -I scripts/make_template.py <wiley>/scripts/report_template.html scripts/report_template.html  # only if the Wiley template changes
python -I scripts/build_report.py work scripts/report_template.html docs/index.html
```
