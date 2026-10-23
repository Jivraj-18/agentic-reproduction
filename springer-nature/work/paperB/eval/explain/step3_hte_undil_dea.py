"""Step 3: HTE undiluted, DEA/NO EC50. The authors' row holds 5.4e-07 M for experiment 5, but that ring
already relaxed 62% at 100 nM. Test: does that one entry explain the published 87 (21-362) nM?"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__)); sys.stdout.reconfigure(encoding="utf-8")
from common import *
D = parse(); P = published(); R = runs()
d = D[("hte_undil", "dea")]
print("Relaxation (%) of each experiment at 30/100/300 nM:")
for e in range(5):
    print(f"  exp{e+1}: " + "/".join(f"{100-x:.0f}" for x in d["tension"][e][3:6]) + f"   authors' EC50 = {d['ec50'][e]*1e9:.0f} nM")
lc = np.log10(CONC)
f = [hill(lc, 100 - d["tension"][e]) for e in range(5)]
print("Own 3p Hill fit EC50 (nM): " + ", ".join(f"{x[1]*1e9:.0f}" for x in f))
def show(tag, ec):
    s = summarise(100 - d["emax_t"], ec)
    print(f"{tag:55s} EC50 {s['ec50']:.1f} ({s['lo']:.1f}-{s['hi']:.1f}) nM")
print("Published: 87 (21-362)")
show("authors' row as deposited (exp5 = 540 nM)", d["ec50"])
alt = d["ec50"].copy(); alt[4] = 5.4e-08
show("authors' row with exp5 = 54 nM (one decimal-place slip)", alt)
alt2 = d["ec50"].copy(); alt2[4] = r2(f[4][1])
show("authors' row with exp5 = own fit (2 s.f.)", alt2)
show("own fits, all five", [x[1] for x in f])
for run in R: print(f"{run}: {R[run]['hte_undil|dea_ec50']:.1f} ({R[run]['hte_undil|dea_lo']:.1f}-{R[run]['hte_undil|dea_hi']:.1f})")
# the paper text on this result
txt = open(os.path.join(PAPER, "source", "paper.txt"), encoding="utf-8").read()
import re
for m in re.finditer(r"[^.]*(?:HTE|THP)[^.]*DEA/NO[^.]*\.", txt): print("Paper:", m.group(0).strip().replace("\n", " "))
