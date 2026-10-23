# Assumptions

- **M3 (gap)**: The 31 M2CA-alone tests = test 1 (A alone) of all 30 deposited combinations (which include the sham M2CA-M2CA) + test 2 (B alone) of the sham M2CA-M2CA, since that test is M2CA tested alone. Rejected: using the sham's mixture test (test 3), because it is a mixture-design test (two dosing streams at halved concentrations), not a single-chemical test.
- **S1 (gap)**: Both duplicate replicates fitted as separate points (14 points per curve), unweighted ordinary least squares (SigmaPlot default). Rejected: averaging duplicates first, and any weighting, because nothing in the methods mentions them.
- **S1/data**: 12 effect readings recorded as "--------------" in the deposit (M2CA-BGE test 1 one replicate at 1.416 uM; M2CA-DEM test 1 one replicate at 0.81 uM; plus B/mixture tests not used here) are treated as missing and dropped; the remaining replicate at that concentration is kept. Rejected: dropping the whole concentration.
- **S1/S3**: Initial values set automatically (EC50 from log-linear interpolation of mean response at 50 %, multistart over Hill slope {0.5,1,2} x s {0.5,1,2}); best fit by least squares. Hill slope bounded to (0.001, 50) for numerical stability only (no fit came near these bounds; none hit the s bounds either).
- **S2 (gap)**: Used the extractor's reconstruction y = 100/(1+(xb/x)^h)^s with xb = EC50 * 10^((1/h) log10(2^(1/s)-1)). EC25/EC75 obtained analytically by inverting this curve: x = xb / ((100/p)^(1/s) - 1)^(1/h). Rejected: none plausible beyond this standard 5PL form.
- **S4 (gap)**: "Slope" = Hill slope parameter h of Eq. 1. r2 = 1 - SSres/SStot over all fitted (replicate) points. Rejected: slope at EC50 on the fitted curve / log-linear slope, because the Hill slope is the model's slope parameter.
- **S5**: TDT computed per test from its own 15- and 45-min fitted EC50s, then summarised across the 31 tests.
- **S6 (gap)**: SD uses n - 1 (sample SD, the SigmaPlot / spreadsheet default); CV = SD/mean x 100; range reported as a single number max - min (the table prints one number). Rejected: population SD (n) and reporting the min-max interval. Shapiro-Wilk W from scipy.stats.shapiro.
- **Stars**: The table has no star legend (star_legend null) and no significance tests, so every `stars` is set to "" (no stars).
- **Units**: Concentrations kept in uM as deposited; no unit changes.
