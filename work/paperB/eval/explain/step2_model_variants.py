"""Step 2: which Hill-type model reproduces the authors' per-experiment fits (their EC50/Emax rows)?
Fit each of the 120 curves under several readings of 'Hill-type model' and compare to the authors' rows."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from common import *
D = parse()
lc = np.log10(CONC)
variants = {
    "3p free nH (baseline 0)": dict(model="3p"),
    "3p, Emax<=100 (Sonnet)": dict(model="3p", emax_max=100),
    "4p free baseline": dict(model="4p"),
    "nH fixed 1": dict(model="3p", nh_fixed=1.0),
}
fits = {}
for v, kw in variants.items():
    for key, d in D.items():
        fits[(v,) + key] = [hill(lc, 100 - d["tension"][e], **kw) for e in range(5)]
# observed max relaxation as Emax
for v, kw in variants.items():
    de, dl = [], []
    for key, d in D.items():
        for e in range(5):
            em, ec, h = fits[(v,) + key][e]
            de.append(em - (100 - d["emax_t"][e])); dl.append(np.log10(ec / d["ec50"][e]))
    de, dl = np.abs(de), np.abs(dl)
    print(f"{v:28s} |dEmax| median {np.median(de):.2f} pts, 90th pct {np.percentile(de,90):.2f}, max {de.max():.1f};"
          f" |log10 EC50 ratio| median {np.median(dl):.3f} (x{10**np.median(dl):.2f}), 90th {np.percentile(dl,90):.3f}, max {dl.max():.2f}")
obs = np.abs([ (100 - d["tension"][e]).max() - (100 - d["emax_t"][e]) for d in D.values() for e in range(5)])
print(f"{'observed max response':28s} |dEmax| median {np.median(obs):.2f}, 90th {np.percentile(obs,90):.2f}, max {obs.max():.1f}")
obs10 = np.abs([ (100 - d["tension"][e][-1]) - (100 - d["emax_t"][e]) for d in D.values() for e in range(5)])
print(f"{'response at 10 uM':28s} |dEmax| median {np.median(obs10):.2f}, 90th {np.percentile(obs10,90):.2f}, max {obs10.max():.1f}")

print("\nLargest per-experiment disagreements (3p free nH vs authors):")
rows = []
for key, d in D.items():
    for e in range(5):
        em, ec, h = fits[("3p free nH (baseline 0)",) + key][e]
        rows.append((abs(np.log10(ec / d["ec50"][e])), key, e + 1, em, ec, h, 100 - d["emax_t"][e], d["ec50"][e],
                     100 - d["tension"][e]))
for r in sorted(rows, key=lambda r: -r[0])[:10]:
    print(f"  {r[1][0]:9s} {r[1][1]} exp{r[2]}: fit Emax {r[3]:.1f} EC50 {r[4]*1e9:.0f} nM nH {r[5]:.2f} | authors Emax {r[6]:.1f} EC50 {r[7]*1e9:.0f} nM"
          f" | relax at 0.1/0.3/1/3/10 uM: " + "/".join(f"{x:.0f}" for x in r[8][4:]))
import pickle; pickle.dump(fits, open(os.path.join(os.path.dirname(__file__), "fits.pkl"), "wb"))
