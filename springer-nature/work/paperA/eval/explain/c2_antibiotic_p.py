"""Cause c2: antibiotic use p printed as <0.001. Try every plausible test and denominator."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats
from _common import load, yn

df = load()
a = yn(df.ATB)
for g in ("NIV", "HFNC"):
    s = a[df.Gr == g]
    print(g, "ATB y/n/md:", int((s == 1).sum()), int((s == 0).sum()), int(s.isna().sum()))
tabs = {
    "complete cases (62/125 vs 49/123)": [[62, 63], [49, 74]],
    "md counted as no (62/126 vs 49/126)": [[62, 64], [49, 77]],
}
for k, t in tabs.items():
    t = np.array(t)
    print(k)
    print("  chi2 Yates        p=%.4f" % stats.chi2_contingency(t, True)[1])
    print("  chi2 uncorrected  p=%.4f" % stats.chi2_contingency(t, False)[1])
    print("  Fisher            p=%.4f" % stats.fisher_exact(t)[1])
    print("  one-sided Fisher  p=%.4f" % stats.fisher_exact(t, alternative="greater")[1])
print("Published: 62 (49%) vs 49 (38%), p<0.001. No test above gives a p below 0.05, let alone <0.001.")
print("The Sedation row (121 vs 54) also has p<0.001, which fits that row; the ATB p looks copied or mistyped.")
