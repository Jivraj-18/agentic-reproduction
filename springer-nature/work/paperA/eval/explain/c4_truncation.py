"""Cause c4: authors cut extra digits (truncate) rather than round in several cells."""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats
from _common import load, num

df = load(); g = df.Gr


def trunc(x, d):
    return math.floor(x * 10 ** d + 1e-9) / 10 ** d


pim = num(df.PIM); mv = num(df.MV)
cells = [
    ("atb|hfnc_pct", 100 * 49 / 126, 0, "38"),
    ("pim|niv_sd", pim[g == "NIV"].std(), 1, "1.7"),
    ("pim|p", stats.mannwhitneyu(pim[g == "NIV"].dropna(), pim[g == "HFNC"].dropna(), method="asymptotic").pvalue, 2, "0.49"),
    ("imv_d|niv_q1", np.quantile(mv[g == "NIV"].dropna(), .25), 1, "3.7"),
]
print("Graded non-A cells:")
for c, v, d, p in cells:
    print(f"  {c:14s} exact={v:.4f}  rounded={round(v, d)}  truncated={trunc(v, d)}  published={p}")
print("Same habit in cells that graded A anyway:")
for c, v, d, p in [("pw|hfnc_pct", 100 * 32 / 126, 1, "25.3"), ("prh|hfnc_pct", 100 * 22 / 126, 1, "17.4"),
                   ("sed|hfnc_pct", 100 * 54 / 126, 1, "42.8")]:
    print(f"  {c:14s} exact={v:.4f}  rounded={round(v, d)}  truncated={trunc(v, d)}  published={p}")
print("Counter-examples (rounded, not truncated): v_me|hfnc_pct 3.17->3.2, v_pa|hfnc_pct 3.97->4; the habit is not uniform.")
