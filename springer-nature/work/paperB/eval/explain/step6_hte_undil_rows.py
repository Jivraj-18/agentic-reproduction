"""Step 6: hte_undil DEA/NO experiments 4 and 5 - do the authors' fitted values belong to these curves?
Search every authors' row for the same (Emax, EC50) pairs, and refit the curves."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__)); sys.stdout.reconfigure(encoding="utf-8")
from common import *
D = parse()
target = D[("hte_undil", "dea")]
for e in (3, 4):
    em, ec = target["emax_t"][e], target["ec50"][e]
    print(f"hte_undil dea exp{e+1}: authors' tension-Emax {em}, EC50 {ec:.2g}")
    for key, d in D.items():
        for j in range(5):
            if key == ("hte_undil", "dea") and j == e: continue
            if abs(d["emax_t"][j] - em) < 1e-9 and abs(d["ec50"][j] - ec) / ec < 1e-9:
                print(f"    identical pair in {key} exp{j+1}")
            elif abs(d["ec50"][j] - ec) / ec < 1e-9:
                print(f"    same EC50 only in {key} exp{j+1} (Emax {d['emax_t'][j]})")
lc = np.log10(CONC)
print("\nRefit of the hte_undil DEA/NO curves (4p free baseline):")
for e in range(5):
    a = hill(lc, 100 - target["tension"][e], model="4p")
    print(f"  exp{e+1}: Emax {a[0]:.1f} (tension {100-a[0]:.1f})  EC50 {a[1]*1e9:.0f} nM | authors tension {target['emax_t'][e]} EC50 {target['ec50'][e]*1e9:.0f} nM")
# table under three readings
P = published()
def show(tag, emt, ec):
    s = summarise(100 - np.asarray(emt), ec)
    print(f"{tag:58s} Emax {s['emax']:.1f} +- {s['sem']:.2f}; EC50 {s['ec50']:.1f} ({s['lo']:.1f}-{s['hi']:.1f})")
print("\nPublished: Emax 96 +- 1.4; EC50 87 (21-362)")
show("authors' rows as deposited", target["emax_t"], target["ec50"])
fit = [hill(lc, 100 - target["tension"][e], model="4p") for e in range(5)]
show("4p refit of all five curves", [100 - round(x[0], 1) for x in fit], [r2(x[1]) for x in fit])
emt = target["emax_t"].copy(); ec = target["ec50"].copy()
emt[3], ec[3] = 100 - round(fit[3][0], 1), r2(fit[3][1]); emt[4], ec[4] = 100 - round(fit[4][0], 1), r2(fit[4][1])
show("authors' rows with exp4+5 replaced by their refits", emt, ec)
