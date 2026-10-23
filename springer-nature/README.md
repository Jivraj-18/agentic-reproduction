# Agentic reproduction of two Springer Nature papers

Blind reproduction of one results table from each of two open-access Springer Nature papers, using only a summary of the Methods and the authors' deposited data. Each table was rebuilt twice, once by Claude Opus 5.5 and once by Claude Sonnet 5.5. Every cell is graded against the published value, and each miss is traced to a cause by re-running the alternative reading.

The publisher's name says whose papers were used. This work is not produced by or for the publisher.

- **Page:** `docs/index.html` (GitHub Pages; same layout as the Wiley page, with an Opus 5.5 / Sonnet 5.5 switch in each paper tab)
- **Write-up, costs and caveats:** `NOTES.md`
- **Pipeline:** `scripts/` (sandbox build, grading, audits, cost, page build); `scripts/EXPLAIN.md` is the explainer's brief
- **Per paper:** `work/paperA`, `work/paperB`: extraction (`extract/`, built by `extract/build_extract.py`), each run's code and assumptions (`sandbox/r_opus`, `sandbox/r_sonnet`), grades, audits, costs and the explainer's tests (`eval/`)

## Papers

- **Paper A:** Santos ACEZ, Caiado CM, Lopes AGD, et al. Comparison between high-flow nasal cannula (HFNC) therapy and noninvasive ventilation (NIV) in children with acute respiratory failure by bronchiolitis: a randomized controlled trial. *BMC Pediatrics* 2024; 24: 595. [doi:10.1186/s12887-024-05058-6](https://doi.org/10.1186/s12887-024-05058-6). Data: [Dryad 10.5061/dryad.4xgxd25jh](https://doi.org/10.5061/dryad.4xgxd25jh).
- **Paper B:** Wölkart G, Kollau A, Russwurm M, et al. Varied effects of tobacco smoke and e-cigarette vapor suggest that nicotine does not affect endothelium-dependent relaxation. *Scientific Reports* 2023; 13: 15833. [doi:10.1038/s41598-023-42750-6](https://doi.org/10.1038/s41598-023-42750-6). Data: [Zenodo 10.5281/zenodo.7963137](https://doi.org/10.5281/zenodo.7963137).

The deposited data are not in this repository (the CC BY papers are, under `work/<paper>/source/`). Download the data from the links above into `work/<paper>/source/data/` to re-run. Rebuild the page with:

```
python -I scripts/make_template.py <wiley>/scripts/report_template.html scripts/report_template.html  # only if the Wiley template changes
python -I scripts/build_report.py work scripts/report_template.html docs/index.html
```
