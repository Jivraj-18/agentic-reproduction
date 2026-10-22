"""Cause: one knot (subject 16, closed knot pusher C, run 1) has loop length 0 before and after 15 N,
so delta knot strength = 0 and spread = 0 (2 mistakes). It is coded 0 in the deposit, not N/A.
log(0) is undefined. Both runs dropped it from the knot-strength model; the Opus run also dropped its spread.
Re-runs knot strength with that zero replaced by several small values, and spread with it kept/dropped."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.filterwarnings("ignore")
from common import *
pub = published(); rv, rg = runs()
d = add_position(load())
print(d[(d.ks <= 0) | (d.sp <= 0)][["subject", "sequence", "tech", "run", "t", "kb", "ka", "ks", "sp", "mi"]].to_string())
print("Smallest non-zero delta knot strength values:", sorted(d.ks[d.ks > 0])[:5], "(data recorded to 0.1 mm)")
ks_cells = [f"ks_{k}|{f}" for k in PAIRS for f in ("eff", "lo", "hi", "p")]
print("\nKnot strength (log scale), published:", {c: pub[c]["raw"] for c in ks_cells})
for pos in (False, True):
    for z in (None, 0.5, 0.1, 0.05, 0.01):
        y = np.log(d["ks"].replace(0, z)) if z is not None else np.log(d["ks"].where(d["ks"] > 0))
        dd = d.assign(y=y)
        r = lmm(dd, "y", extra=" + C(pos)" if pos else "")
        vals = {f"ks_{k}|{f}": (r[k]["p"] if f == "p" else float(np.exp(r[k]["est" if f == "eff" else f]))) for k in PAIRS for f in ("eff", "lo", "hi", "p")}
        nA = sum(grade(c, rnd(c, vals[c], pub), pub)[0] == "A" for c in ks_cells)
        lab = f"zero->{'dropped' if z is None else z} {'+pos' if pos else '    '}"
        print(f"  {lab:20s} n={r['_n']} A={nA}/12 ", fmt(r, np.exp))
# log(x+1) style offsets for completeness
for off in (1.0, 0.1):
    r = lmm(d.assign(y=np.log(d["ks"] + off)), "y", extra=" + C(pos)")
    print(f"  log(ks+{off}) +pos     ", fmt(r, np.exp))

print("\nCell by cell, zero dropped (both runs) vs zero -> 0.1 mm, both with the position term; last column adds t-based p (df = n - p - (subjects-1)):")
dz = d.assign(y=np.log(d["ks"].replace(0, 0.1)))
r = lmm(dz, "y", extra=" + C(pos)")
n = r["_n"]; df = n - 7 - (d.subject.nunique() - 1)
for k in PAIRS:
    for f in ("eff", "lo", "hi", "p"):
        c = f"ks_{k}|{f}"
        v = r[k]["p"] if f == "p" else float(np.exp(r[k]["est" if f == "eff" else f]))
        extra = ""
        if f == "p":
            zst = stats.norm.isf(v / 2); extra = f"  t-based p={2 * stats.t.sf(zst, df):.4f} (df={df})"
        print(f"  {c:10s} published={pub[c]['raw']:>6s} opus={rv[c]['r_opus']:.4f}({rg[c]['r_opus']}) sonnet={rv[c]['r_sonnet']:.4f}({rg[c]['r_sonnet']}) alt={v:.4f} -> {grade(c, rnd(c, v, pub), pub)[0]}{extra}")

print("\nKnot-spread ability: zero spread kept (Sonnet) vs dropped (Opus), with and without position term")
sp_cells = [f"sp_{k}|{f}" for k in PAIRS for f in ("eff", "lo", "hi", "p")]
for drop in (False, True):
    for pos in (False, True):
        dd = d.copy()
        if drop: dd.loc[dd.sp == 0, "sp"] = np.nan
        r = lmm(dd, "sp", extra=" + C(pos)" if pos else "")
        vals = {f"sp_{k}|{f}": (r[k]["p"] if f == "p" else r[k]["est" if f == "eff" else f]) for k in PAIRS for f in ("eff", "lo", "hi", "p")}
        nA = sum(grade(c, rnd(c, vals[c], pub), pub)[0] == "A" for c in sp_cells)
        print(f"  zero {'dropped' if drop else 'kept   '} {'+pos' if pos else '    '} n={r['_n']} A={nA}/12 ", fmt(r))
        if drop and not pos:
            for c in sp_cells:
                if rg[c]["r_opus"] != "A":
                    print(f"     {c:10s} published={pub[c]['raw']:>6s} opus={rv[c]['r_opus']:.4f}({rg[c]['r_opus']}) this re-run={vals[c]:.4f}")

print("\nIndependent check from the paper's Table 2: closed technique (C), run 1, mean knot strength is printed 5.59.")
x = d[(d.tech == "C") & (d.run == 1)]["ks"]
print(f"  zero kept as 0: {x.mean():.4f} | zero dropped: {x[x > 0].mean():.4f} | zero set to 0.1: {x.replace(0, 0.1).mean():.4f}")
print("  Only the 0.1 mm reading gives 5.59 (5.586).")
