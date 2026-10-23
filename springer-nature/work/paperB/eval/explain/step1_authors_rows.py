"""Step 1: does the authors' own per-experiment fit row (in the deposit) give the published table?
Also: how close are the runs' unrounded per-experiment fits to the authors' rows?"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from common import *
D = parse(); P = published(); R = runs()
cols = ["emax", "sem", "ec50", "lo", "hi"]
nA = 0; tot = 0; miss = []
print("Table rebuilt from the authors' own fitted rows (Emax row is % tension remaining -> relaxation = 100 - it)")
for (rid, ag), d in D.items():
    s = summarise(100 - d["emax_t"], d["ec50"])
    line = []
    for c in cols:
        pub, dec = P[f"{rid}|{ag}_{c}"]
        g = grade(pub, s[c], dec); tot += 1; nA += g == "A"
        if g != "A": miss.append((rid, ag, c, pub, s[c]))
        line.append(f"{c}={s[c]:.4g}(pub {pub:g},{g})")
    print(f"{rid:9s} {ag}: " + "  ".join(line))
print(f"\nAuthors' rows reproduce {nA}/{tot} cells at grade A. Non-A: {miss}")
