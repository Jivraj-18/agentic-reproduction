"""Causes c6/c7: cells no tried reading reproduces (WDF spread and p, NGT p, IMV HFNC Q3, duration NIV Q3)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats
from _common import load, num

df = load(); g = df.Gr


def tests(v, lab):
    x, y = v[g == "NIV"].dropna(), v[g == "HFNC"].dropna()
    print(f"  {lab}: n={len(x)}/{len(y)} mean={x.mean():.3f}/{y.mean():.3f} sd={x.std():.3f}/{y.std():.3f}"
          f"  MW cc p={stats.mannwhitneyu(x, y, method='asymptotic').pvalue:.4f}"
          f"  MW no-cc p={stats.mannwhitneyu(x, y, method='asymptotic', use_continuity=False).pvalue:.4f}"
          f"  t p={stats.ttest_ind(x, y).pvalue:.4f}  Welch p={stats.ttest_ind(x, y, equal_var=False).pvalue:.4f}")


print("Initial WDF (published mean 5.9/5.9, SD 0.9/1.1, p 0.9):")
for t in ["WD_0", "WD_2"]:
    tests(num(df[t]), t)
print("  Swap check: published NIV 0.9 / HFNC 1.1; data 0.99 / 0.88. Swapping gives 0.9 / 1.0, still not 1.1.")
print("Nasogastric tube days (published p 0.012):")
e = num(df.ETu)
tests(e, "ETu, tube users only (both runs)")
e0 = e.copy(); e0[df.ETu.astype(str).str.strip() == "nc"] = 0
tests(e0, "ETu, 'nc' as 0 days")
print("IMV days, HFNC (published 4 (2.5-4.5)):")
mv = num(df.MV)
for lab, sel in [("all recorded (both runs)", mv.notna()), ("intubated only (It=y)", mv.notna() & (df.It == "y"))]:
    z = mv[sel & (g == "HFNC")].values
    for m in ["linear", "weibull", "hazen", "inverted_cdf", "averaged_inverted_cdf", "median_unbiased"]:
        print(f"  {lab:26s} {m:22s} n={len(z)} Q1/med/Q3 = {np.quantile(z, [.25, .5, .75], method=m).tolist()}")
print("  Sorted HFNC MV:", sorted(mv[g == "HFNC"].dropna().astype(int).tolist()))
print("  4.5 would need the 75th centile to fall between a 4 and a 5; with 27 values it sits among the 5s.")
