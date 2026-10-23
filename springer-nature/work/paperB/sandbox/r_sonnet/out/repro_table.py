import sys, os, json
import numpy as np, pandas as pd
from scipy import stats
from scipy.optimize import least_squares

data_dir, out_dir = sys.argv[1], sys.argv[2]
df = pd.read_csv(os.path.join(data_dir, "aorta_crc.csv"))
df["relax"] = 100.0 - df["pct_of_precontraction"]   # M1

ROWMAP = {
 "cse_ctrl": ("CSE", "Control (DMEM)"), "cse_3": ("CSE", "CSE 1:3 Verd."),
 "cse_20": ("CSE", "CSE 1:20 Verd."), "cse_200": ("CSE", "CSE  1:200 Verd."),
 "eve_ctrl": ("EVE", "Control (DMEM)"), "eve_undil": ("EVE", "EVE unv."),
 "eve_2": ("EVE", "EVE 1:2"), "eve_20": ("EVE", "EVE 1:20"),
 "hte_ctrl": ("HTE", "Control (DMEM)"), "hte_undil": ("HTE", "HTE unv."),
 "hte_2": ("HTE", "HTE 1:2"), "hte_20": ("HTE", "HTE 1:20"),
}
AG = {"ach": "acetylcholine", "dea": "DEA/NO"}

def hill_fit(logc, y):
    """R = Emax*c^h/(EC50^h+c^h), baseline fixed at 0, free slope. Fit on log10 EC50."""
    def res(p):
        emax, lec, h = p
        return emax / (1 + 10 ** (h * (lec - logc))) - y
    best = None
    for lec0 in np.arange(-9, -4.4, 0.5):
        for h0 in (0.7, 1.0, 1.5):
            try:
                r = least_squares(res, [min(max(y.max(), 5), 100), lec0, h0],
                                  bounds=([0, -11, 0.2], [100, -2, 5]))
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    return best.x

def fit_group(sub):
    out = []
    for e, g in sub.groupby("experiment"):
        g = g.sort_values("conc_M")
        out.append(hill_fit(np.log10(g.conc_M.values), g.relax.values))
    return np.array(out)  # n x (emax, log10ec50 [M], h)

fits = {}
for rid, (ex, tr) in ROWMAP.items():
    for ak, an in AG.items():
        sub = df[(df.extract == ex) & (df.treatment == tr) & (df.agonist == an)]
        assert sub.experiment.nunique() == 5, (rid, ak)
        fits[(rid, ak)] = fit_group(sub)

tpl = json.load(open("template.json")) if os.path.exists("template.json") else None
if tpl is None:
    tpl = json.load(open(os.path.join(data_dir, "..", "template.json")))

cells = tpl["cells"]
for (rid, ak), f in fits.items():
    emax = f[:, 0]; lec = f[:, 1] + 9  # log10 nM
    n = len(emax)
    m, sem = emax.mean(), emax.std(ddof=1) / np.sqrt(n)
    lm, ls = lec.mean(), lec.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.975, n - 1)
    src = "fit_group/hill_fit (per-experiment Hill fit) + summary"
    for col, v in ((f"{ak}_emax", m), (f"{ak}_sem", sem), (f"{ak}_ec50", 10 ** lm),
                   (f"{ak}_lo", 10 ** (lm - t * ls)), (f"{ak}_hi", 10 ** (lm + t * ls))):
        c = cells[f"{rid}|{col}"]
        c["value"] = float(v); c["stars"] = ""; c["source"] = src
        c["unit"] = "%" if "emax" in col or "sem" in col else "nM"

# Dunnett vs series control on per-experiment Emax
for ex in ("cse", "eve", "hte"):
    rows = [r for r in ROWMAP if r.startswith(ex)]
    for ak in AG:
        ctrl = fits[(f"{ex}_ctrl", ak)][:, 0]
        trt = [r for r in rows if not r.endswith("ctrl")]
        res = stats.dunnett(*[fits[(r, ak)][:, 0] for r in trt], control=ctrl)
        for r, p in zip(trt, res.pvalue):
            c = cells[f"{r}|{ak}_emax"]
            c["stars"] = "*" if p < 0.05 else ""
            c["source"] = "scipy.stats.dunnett on per-experiment Emax"
            print(f"Dunnett {r} {ak}: p={p:.4g}")

for k, c in cells.items():
    if c["value"] is None: print("MISSING", k)
json.dump(tpl, open(os.path.join(out_dir, "filled.json"), "w"), indent=1)
for rid in ROWMAP:
    print(rid, *[f"{cells[f'{rid}|{c}']['value']:.4g}{cells[f'{rid}|{c}']['stars']}" for c in
          ("ach_emax","ach_sem","ach_ec50","ach_lo","ach_hi","dea_emax","dea_sem","dea_ec50","dea_lo","dea_hi")])
