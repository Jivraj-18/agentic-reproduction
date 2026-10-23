"""Cause c1: chi-square p values for 2x2 rows - Yates continuity correction or not."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats
from _common import load, yn

df = load()
rows = {"female": df.Gn.astype(float), "pw": yn(df.PW), "prh": yn(df.PRH)}
pub = {"female": "0.15", "pw": "0.3", "prh": "0.2"}
print(f"{'row':8s}{'published':>10s}{'Yates (both runs)':>20s}{'no correction':>16s}{'Fisher':>10s}")
for r, f in rows.items():
    t = np.array([[((f == 1) & (df.Gr == g)).sum(), ((f == 0) & (df.Gr == g)).sum()] for g in ("NIV", "HFNC")])
    py = stats.chi2_contingency(t, correction=True)[1]
    pn = stats.chi2_contingency(t, correction=False)[1]
    pf = stats.fisher_exact(t)[1]
    print(f"{r:8s}{pub[r]:>10s}{py:20.4f}{pn:16.4f}{pf:10.4f}   table={t.tolist()}")
