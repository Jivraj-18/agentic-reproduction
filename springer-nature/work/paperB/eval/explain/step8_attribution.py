"""Step 8: best reconstruction of the authors' pipeline and assignment of every non-A cell of each run to a cause.
Reconstruction: per experiment, 4-parameter Hill fit (free baseline, free slope); a fitted Emax above 100% is
reported as 100% (the authors' sheet shows tension-Emax '0' for exactly those curves) while the EC50 is kept;
EC50 kept to 2 significant figures and Emax to 0.1 (as the sheet holds them); mean +- SEM and geometric mean with
t(4) 95% limits. Run-specific check for Opus: same 3p model as Opus, but cut Emax at 100% instead of refitting
with slope 1."""
import sys, os, json, pickle; sys.path.insert(0, os.path.dirname(__file__)); sys.stdout.reconfigure(encoding="utf-8")
from common import *
D = parse(); P = published(); R = runs()
G = json.load(open(os.path.join(PAPER, "eval", "grades.json"), encoding="utf-8"))["cells"]
fits = pickle.load(open(os.path.join(os.path.dirname(__file__), "fits.pkl"), "rb"))
lc = np.log10(CONC); cols = ["emax", "sem", "ec50", "lo", "hi"]

def build(getfit, clip=True, rnd=True):
    T = {}
    for key in D:
        f = [getfit(key, e) for e in range(5)]
        em = [min(x[0], 100) if clip else x[0] for x in f]; ec = [x[1] for x in f]
        if rnd: em = [round(x, 1) for x in em]; ec = [r2(x) for x in ec]
        s = summarise(em, ec)
        for c in cols: T[f"{key[0]}|{key[1]}_{c}"] = s[c]
    return T
def grades(T): return {k: grade(P[k][0], v, P[k][1]) for k, v in T.items()}

T4 = build(lambda k, e: fits[("4p free baseline",) + k][e]); G4 = grades(T4)
T4n = build(lambda k, e: fits[("4p free baseline",) + k][e], clip=False); G4n = grades(T4n)
T3 = build(lambda k, e: fits[("3p free nH (baseline 0)",) + k][e], rnd=False); G3 = grades(T3)
# Opus rule: 3p free; fallback to nH=1 if EC50>10uM, Emax>100 or slope at a bound
def opus_fit(k, e, clip_instead=False):
    y = 100 - D[k]["tension"][e]; em, ec, h = hill(lc, y, emax_max=200)
    bad100 = em > 100; badother = ec > 1e-5 or h <= 0.2001 or h >= 4.999
    if badother or (bad100 and not clip_instead): return hill(lc, y, nh_fixed=1.0, emax_max=200)
    return (min(em, 100), ec, h)
TO = build(lambda k, e: opus_fit(k, e), clip=False, rnd=False); GO = grades(TO)
TOc = build(lambda k, e: opus_fit(k, e, True), clip=False, rnd=False); GOc = grades(TOc)
print("Check: Opus rule re-implemented vs Opus's own filled values (max abs rel diff over cells):",
      f"{max(abs(TO[k]-R['r_opus'][k])/abs(R['r_opus'][k]) for k in TO):.4f}")
for name, g in (("3p baseline-0 (runs' model)", G3), ("4p, no Emax cut", G4n), ("4p + Emax cut at 100% + sheet rounding", G4)):
    print(f"{name:45s}", {x: sum(1 for v in g.values() if v == x) for x in "ABCDE"})

causes = {}
for run in ("r_opus", "r_sonnet"):
    bad = [k for k, c in G.items() if c["runs"][run]["grade"] != "A"]
    for k in bad:
        if k.startswith("cse_3|ach"): c = "c3_flat_curve"
        elif k.startswith("hte_undil|dea_") and k.split("_")[-1] in ("sem", "ec50", "lo", "hi"): c = "c4_hte_undil_rows"
        elif run == "r_opus" and GO[k] != "A" and GOc[k] == "A": c = "c2_emax_over_100"
        elif G4[k] == "A": c = "c1_baseline"
        else: c = "c5_residual"
        causes.setdefault(run, {}).setdefault(c, []).append(k)
for run in causes:
    print(f"\n== {run}")
    for c, ks in sorted(causes[run].items()):
        print(f"  {c} ({len(ks)} cells)")
        for k in ks:
            print(f"     {k:20s} pub {P[k][0]:<6g} run {R[run][k]:9.4g} ({G[k]['runs'][run]['grade']})  "
                  f"4p+cut {T4[k]:9.4g} ({G4[k]})" + (f"  opus-with-cut {TOc[k]:9.4g} ({GOc[k]})" if run == "r_opus" else ""))
json.dump(causes, open(os.path.join(os.path.dirname(__file__), "attribution.json"), "w"), indent=1)
print("\nAll cells still non-A under 4p + cut + rounding:")
for k, g in G4.items():
    if g != "A": print(f"   {k:20s} pub {P[k][0]:g}  recon {T4[k]:.4g} ({g})")
