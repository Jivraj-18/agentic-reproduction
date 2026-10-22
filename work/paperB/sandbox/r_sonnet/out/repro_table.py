import sys, json, os, warnings
import numpy as np, pandas as pd
from scipy.optimize import least_squares
from scipy.stats import shapiro
warnings.filterwarnings("ignore")
data_dir, out_dir = sys.argv[1], sys.argv[2]
d = pd.read_csv(os.path.join(data_dir, "raw_crc.csv"))
d["effect_pct"] = pd.to_numeric(d["effect_pct"], errors="coerce")  # "--------------" = missing reading

def model(p, x):
    ec50, h, s = p
    xb = ec50 * 10 ** ((1.0 / h) * np.log10(2 ** (1.0 / s) - 1))
    return 100.0 / (1 + (xb / x) ** h) ** s

def fit(x, y):
    best = None
    xm = np.median(x)
    for e0 in [xm / 4, xm, xm * 4, x.max(), x.max() * 5]:
        for h0 in [0.7, 1.5, 3, 6]:
            for s0 in [0.3, 1, 3]:
                try:
                    r = least_squares(lambda p: model(p, x) - y, [e0, h0, s0],
                        bounds=([1e-9, 0.05, 0.1], [np.inf, 50, 10]), x_scale=[e0, 1, 1])
                except Exception:
                    continue
                if best is None or r.cost < best.cost - 1e-12:
                    best = r
    ec50, h, s = best.x
    xb = ec50 * 10 ** ((1.0 / h) * np.log10(2 ** (1.0 / s) - 1))
    ecx = lambda p: xb / ((100.0 / p) ** (1.0 / s) - 1) ** (1.0 / h)
    ss_res = 2 * best.cost
    r2 = 1 - ss_res / np.sum((y - y.mean()) ** 2)
    return dict(ec25=ecx(25), ec50=ec50, ec75=ecx(75), slope=h, s=s, r2=r2)

# 31 M2CA-alone tests: test 1 of each of 30 combos + test 2 (B alone = M2CA) of sham
sel = [(c, 1) for c in d.combination.unique()] + [("M2CA-M2CA", 2)]
res = []
for c, t in sel:
    sub = d[(d.combination == c) & (d.test == t)]
    xc = "conc_B_uM" if t == 2 else "conc_A_uM"
    row = {"combo": c, "test": t}
    for tm in (15, 30, 45):
        q = sub[(sub.time_min == tm)].dropna(subset=["effect_pct"])
        f = fit(q[xc].values.astype(float), q.effect_pct.values.astype(float))
        for k, v in f.items():
            row[f"{k}_{tm}"] = v
    row["tdt_15_45"] = (row["ec50_15"] - row["ec50_45"]) / (row["ec50_15"] * 0.667) * 100
    res.append(row)
R = pd.DataFrame(res)
R.to_csv(os.path.join(out_dir, "per_test_fits.csv"), index=False)
print(R.round(4).to_string())

tpl = json.load(open(os.path.join(out_dir, "..", "template.json")))
for key, cell in tpl["cells"].items():
    rid, col = key.split("|")
    v = R[rid].values
    if col == "mean": val = v.mean()
    elif col == "sd": val = v.std(ddof=1)
    elif col == "cv": val = v.std(ddof=1) / v.mean() * 100
    elif col == "range": val = v.max() - v.min()
    elif col == "sw": val = shapiro(v).statistic
    cell["value"] = float(val); cell["stars"] = ""
    cell["source"] = f"fit() 5PL-1P per test/time -> column {rid}; stat {col} over n={len(v)}"
json.dump(tpl, open(os.path.join(out_dir, "filled.json"), "w"), indent=1, ensure_ascii=False)
for rid in [r["id"] for r in tpl["rows"]]:
    print(rid, *[round(tpl["cells"][f"{rid}|{c}"]["value"], 4) for c in ("mean","sd","cv","range","sw")])
