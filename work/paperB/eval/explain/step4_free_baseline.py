"""Step 4: re-run the table with a 4-parameter Hill fit (free baseline, free slope) per experiment,
the reading that best matches the authors' own fitted rows (step 2). Grade every cell against the
published value, and show which of the runs' non-A cells move to A."""
import sys, os, json, pickle; sys.path.insert(0, os.path.dirname(__file__)); sys.stdout.reconfigure(encoding="utf-8")
from common import *
D = parse(); P = published(); R = runs()
G = json.load(open(os.path.join(PAPER, "eval", "grades.json"), encoding="utf-8"))["cells"]
fits = pickle.load(open(os.path.join(os.path.dirname(__file__), "fits.pkl"), "rb"))
cols = ["emax", "sem", "ec50", "lo", "hi"]
def table(variant, rounding=False):
    T = {}
    for key, d in D.items():
        f = fits[(variant,) + key]
        em = [x[0] for x in f]; ec = [x[1] for x in f]
        if rounding:
            em = [round(x, 1) for x in em]; ec = [r2(x) for x in ec]
        s = summarise(em, ec)
        for c in cols: T[f"{key[0]}|{key[1]}_{c}"] = s[c]
    return T
for variant in ("3p free nH (baseline 0)", "4p free baseline"):
    for rnd in (False, True):
        T = table(variant, rnd)
        gs = {k: grade(*P[k], ) if False else grade(P[k][0], v, P[k][1]) for k, v in T.items()}
        dist = {g: sum(1 for x in gs.values() if x == g) for g in "ABCDE"}
        print(f"{variant}{' + EC50 to 2 s.f., Emax to 0.1' if rnd else ''}: {dist}")
        if variant.startswith("4p") and rnd:
            T4 = T; G4 = gs
print("\nPer run non-A cell -> grade under 4p free-baseline fit (rounded like the authors' sheet):")
for run in ("r_opus", "r_sonnet"):
    bad = [k for k, c in G.items() if c["runs"][run]["grade"] != "A"]
    moved = [k for k in bad if G4[k] == "A"]
    print(f"\n{run}: {len(bad)} non-A, {len(moved)} become A under 4p; still non-A:")
    for k in bad:
        if G4[k] != "A":
            print(f"   {k:20s} pub {P[k][0]:g}  run {R[run][k]:.4g} ({G[k]['runs'][run]['grade']})  4p {T4[k]:.4g} ({G4[k]})")
print("\nAll cells non-A under 4p (rounded):")
for k, g in G4.items():
    if g != "A": print(f"   {k:20s} pub {P[k][0]:g}  4p {T4[k]:.4g} ({g})")
print("\nExamples:")
for k in ["cse_ctrl|ach_sem", "cse_ctrl|ach_lo", "eve_20|dea_sem", "eve_2|dea_ec50", "hte_ctrl|ach_lo", "cse_200|ach_hi"]:
    print(f"   {k:20s} pub {P[k][0]:g}  opus {R['r_opus'][k]:.4g}  sonnet {R['r_sonnet'][k]:.4g}  4p {T4[k]:.4g} ({G4[k]})")
json.dump({k: [v, G4[k]] for k, v in T4.items()}, open(os.path.join(os.path.dirname(__file__), "table_4p.json"), "w"), indent=0)
