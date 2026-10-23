"""Cause: which 'mean' is printed in brackets. Re-computes the bracketed means three ways."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.filterwarnings("ignore")
from common import *
pub = published(); rv, rg = runs()
d = load()
print("Per technique x run arithmetic means (these are the bracketed values of the paper's Table 2):")
for col in ("t", "ks", "sp", "mi", "mb"):
    x = d.dropna(subset=[col])
    print(col, "\n", x.groupby(["tech", "run"])[col].mean().unstack().round(2).to_string())
print("\nTechnique means three ways (pooled over valid runs | average of the three run means | per participant first):")
for col in ("t", "ks", "sp", "mi", "mb"):
    x = d.dropna(subset=[col])
    print(f"{col:3s} pooled", x.groupby("tech")[col].mean().round(3).to_dict(),
          "| run-means", x.groupby(["tech", "run"])[col].mean().groupby("tech").mean().round(3).to_dict(),
          "| subject-first", x.groupby(["tech", "subject"])[col].mean().groupby("tech").mean().round(3).to_dict())
print("(mb = share of runs with >=1 mistake; mi = mean mistake count)")
alt = table(means="runmeans")
cells = [c for c in pub if c.endswith("|m1") or c.endswith("|m2")]
print("\nAlternative reading: average of the three per-run arithmetic means")
bad = {r: [c for c in cells if rg[c][r] != "A"] for r in ("r_opus", "r_sonnet")}
for r in bad:
    print(r, "non-A mean cells:", len(bad[r]))
    for c in bad[r]:
        gr, dev = grade(c, rnd(c, alt[c], pub), pub)
        print(f"  {c:10s} published={pub[c]['raw']:>6s} run={rv[c][r]:9.4f} ({rg[c][r]})  alt={alt[c]:9.4f} -> {gr} ({dev:.1f}%)")
print("\nAll 24 mean cells under the alternative:", {g: sum(grade(c, rnd(c, alt[c], pub), pub)[0] == g for c in cells) for g in "ABCDE"})
for c in cells:
    print(f"  {c:10s} published={pub[c]['raw']:>6s} alt={alt[c]:8.3f} {grade(c, rnd(c, alt[c], pub), pub)[0]}")
from fractions import Fraction
x = d.dropna(subset=["mi"])
fr = {t: sum(Fraction(int(s), int(n)) for s, n in x[x.tech == t].groupby("run")["mi"].agg(["sum", "count"]).values) / 3 for t in "ABC"}
print("\nExact mistake means (fractions):", {t: f"{v} = {float(v):.6f}" for t, v in fr.items()})
print("Technique B is exactly 0.275; the float sum above gives 0.27499999..., which rounds down to 0.27,")
print("but the exact value (and R's round/sprintf on 0.275, stored as 0.27500000000000002) prints 0.28, the published value.")
