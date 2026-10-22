"""Cause c5 (and dur|niv_q3 in c6): the NIV duration value written '17h'."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats
from _common import load, num

df = load(); g = df.Gr
print("Raw NIV TD entries that are not plain numbers:", [v for v in df.TD[g == "NIV"].astype(str) if not v.isdigit()])
for lab, ph in [("'17h' read as 17 h (Opus)", True), ("'17h' dropped (Sonnet)", False)]:
    td = num(df.TD, parse_h=ph)
    x, y = td[g == "NIV"].dropna().values, td[g == "HFNC"].dropna().values
    p = stats.mannwhitneyu(x, y, method="asymptotic", use_continuity=True).pvalue
    print(f"{lab}: n_NIV={len(x)}  p={p:.6f} (published 0.0003)")
    for m in ["inverted_cdf", "averaged_inverted_cdf", "closest_observation", "interpolated_inverted_cdf",
              "hazen", "weibull", "linear", "median_unbiased", "normal_unbiased"]:
        q = np.quantile(x, [.25, .5, .75], method=m)
        print(f"    {m:26s} Q1={q[0]:.2f} median={q[1]:.2f} Q3={q[2]:.2f}   (published 24 / 48 / 78)")
xs = np.sort(num(df.TD)[g == "NIV"].dropna().values)
print("NIV sorted values around Q3:", xs[88:100].tolist(), "- 78 is not a value, and no quantile rule lands on it.")
