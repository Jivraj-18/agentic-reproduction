"""Step 9: (a) the six cells still B under the reconstruction - are they rounding edges?
(b) Significance stars on the Emax column computed from the authors' own rows."""
import sys, os, pickle; sys.path.insert(0, os.path.dirname(__file__)); sys.stdout.reconfigure(encoding="utf-8")
from common import *
from scipy import stats
D = parse(); P = published()
fits = pickle.load(open(os.path.join(os.path.dirname(__file__), "fits.pkl"), "rb"))
print("(a) Per-experiment EC50s that sit on a 2-significant-figure rounding edge (4p fit vs authors' sheet):")
for key in [("cse_200", "ach"), ("eve_ctrl", "ach"), ("hte_ctrl", "ach")]:
    f = fits[("4p free baseline",) + key]
    print(f"   {key}: fit " + ", ".join(f"{x[1]*1e9:.2f}" for x in f) + " nM | sheet " + ", ".join(f"{x*1e9:.0f}" for x in D[key]["ec50"]))
cells = ["cse_200|ach_lo", "eve_ctrl|ach_lo", "hte_ctrl|ach_hi", "eve_undil|dea_sem", "eve_20|ach_sem", "eve_undil|dea_ec50"]
print("\n   Same cells from the authors' own (rounded) rows:")
for c in cells:
    rid, rest = c.split("|"); ag, col = rest.split("_")
    d = D[(rid, ag)]; s = summarise(100 - d["emax_t"], d["ec50"])
    print(f"   {c:20s} authors' rows {s[col]:.4g} -> grade {grade(P[c][0], s[col], P[c][1])} (published {P[c][0]:g})")
print("   eve_20|ach_sem: 4.549 printed as 4.6 (4.549 -> 4.55 -> 4.6); eve_undil|dea_ec50: 43.49 printed as 44 (-> 43.5 -> 44):"
      " the printed value rounds an already rounded number.")
print("\n(b) Dunnett vs control on the authors' Emax rows (relaxation %):")
for ser, rows in (("cse", ["cse_3", "cse_20", "cse_200"]), ("eve", ["eve_undil", "eve_2", "eve_20"]), ("hte", ["hte_undil", "hte_2", "hte_20"])):
    for ag in ("ach", "dea"):
        ctrl = 100 - D[(f"{ser}_ctrl", ag)]["emax_t"]
        r = stats.dunnett(*[100 - D[(x, ag)]["emax_t"] for x in rows], control=ctrl)
        print(f"   {ser} {ag}: " + ", ".join(f"{x} p={p:.3g}" for x, p in zip(rows, r.pvalue)))
