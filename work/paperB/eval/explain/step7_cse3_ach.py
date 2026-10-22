"""Step 7: CSE 1:3, acetylcholine. Curves barely rise (max relaxation 6-23%), so a free Hill fit is ill-posed.
Which fitting rule reproduces the authors' per-experiment rows and the published 17 +- 3.8, 806 (233-2790)?"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__)); sys.stdout.reconfigure(encoding="utf-8")
from common import *
from scipy.optimize import least_squares
D = parse(); P = published(); R = runs()
d = D[("cse_3", "ach")]; lc = np.log10(CONC)
Y = [100 - d["tension"][e] for e in range(5)]
def fit4(y, lec_max=-2, top_max=np.inf, h_fixed=None):
    best = None
    for lec0 in np.arange(-9, -4.4, 0.25):
        for h0 in ((h_fixed,) if h_fixed else (0.5, 1.0, 1.5, 2.5)):
            def res(p):
                b, top, lec = p[:3]; h = h_fixed or p[3]
                return b + (top - b) / (1 + 10 ** (h * (lec - lc))) - y
            p0 = [0, max(y.max(), 5), min(lec0, lec_max - 1e-3)] + ([] if h_fixed else [h0])
            lb = [-20, 0, -11] + ([] if h_fixed else [0.2]); ub = [20, top_max, lec_max] + ([] if h_fixed else [5])
            r = least_squares(res, p0, bounds=(lb, ub))
            if best is None or r.cost < best.cost: best = r
    p = best.x; return p[1], 10 ** p[2], (h_fixed or p[3]), best.cost * 2
print("Relaxation (%) at 1 nM..10 uM:")
for e in range(5): print(f"  exp{e+1}: " + " ".join(f"{x:5.1f}" for x in Y[e]) + f"   authors: Emax {100-d['emax_t'][e]:.1f}, EC50 {d['ec50'][e]*1e9:.0f} nM")
rules = {
    "4p free (global least squares)": dict(),
    "4p, EC50 <= 10 uM (top of tested range)": dict(lec_max=-5),
    "4p, EC50 <= 3 uM": dict(lec_max=np.log10(3e-6)),
    "4p, slope fixed 1": dict(h_fixed=1.0),
    "4p, Emax <= observed max + 10": None,
}
print("\nPer-experiment fits (Emax %, EC50 nM, nH, SSE):")
res_tab = {}
for name, kw in rules.items():
    out = []
    for e in range(5):
        k = kw if kw is not None else dict(top_max=Y[e].max() + 10)
        out.append(fit4(Y[e], **k))
    res_tab[name] = out
    print(f"  {name}:")
    for e, o in enumerate(out):
        print(f"     exp{e+1}: Emax {o[0]:7.1f} EC50 {o[1]*1e9:10.0f} nH {o[2]:.2f} SSE {o[3]:.2f}")
    s = summarise([round(o[0], 1) for o in out], [r2(o[1]) for o in out])
    print(f"     -> table: Emax {s['emax']:.1f} +- {s['sem']:.2f}; EC50 {s['ec50']:.0f} ({s['lo']:.0f}-{s['hi']:.0f})")
# SSE of authors' parameters for exp1/exp2 at their reported Emax/EC50 (best baseline & slope)
print("\nSSE at the authors' Emax/EC50 (baseline and slope re-optimised) vs global minimum:")
for e in range(5):
    top, ec = 100 - d["emax_t"][e], d["ec50"][e]
    def res(p): b, h = p; return b + (top - b) / (1 + 10 ** (h * (np.log10(ec) - lc))) - Y[e]
    r = min((least_squares(res, [0, h0], bounds=([-20, 0.2], [20, 5])) for h0 in (0.5, 1, 2, 3)), key=lambda r: r.cost)
    print(f"  exp{e+1}: authors' point SSE {2*r.cost:.2f} (nH {r.x[1]:.2f}); global 4p SSE {res_tab['4p free (global least squares)'][e][3]:.2f}")
print(f"\nPublished: Emax 17 +- 3.8; EC50 806 (233-2790)")
for run in R: print(f"{run}: Emax {R[run]['cse_3|ach_emax']:.1f} +- {R[run]['cse_3|ach_sem']:.2f}; EC50 {R[run]['cse_3|ach_ec50']:.0f} ({R[run]['cse_3|ach_lo']:.0f}-{R[run]['cse_3|ach_hi']:.0f})")
