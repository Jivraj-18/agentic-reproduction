import sys, os, glob, json
import numpy as np, pandas as pd
from scipy.stats import wilcoxon

data_dir, out_dir = sys.argv[1], sys.argv[2]
f = glob.glob(os.path.join(data_dir, "*.xlsx"))[0]
raw = pd.read_excel(f, header=0)
df = raw[pd.to_numeric(raw.iloc[:, 0], errors="coerce").notna()].copy()  # participant rows only
df.columns = [str(c).strip() for c in df.columns]
print("participants:", len(df))
tmpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "template.json")
T = json.load(open(tmpl))

def col(prefix, suffix):
    for c in df.columns:
        if c.lower().replace(" ", "").startswith(prefix.lower().replace(" ", "") + suffix.lower()):
            return c
    raise KeyError(prefix + suffix)

# row id -> column name prefix, up to the " B"/" F" marker
ROWS = {
 "fvc_sit": "FVC sitting", "fvc_lie": "FVC lying", "hip_flex": "Hip flexion",
 "hip_add": "Hip Adduction", "hip_abd": "Hip Abduction", "knee_ext": "Knee Extension",
 "knee_flex": "Knee Flexion", "ankle_df": "Ankle Dorsiflexion", "smwt": "Six minute walk",
 "tug": "Timed up and go velocity", "tmwr": "Ten metre walk or run velocity",
 "stair_up": "Stair ascent velocity", "stair_down": "Stair descent velocity", "chair": "Chair Rise",
}
def getcols(prefix):
    b = [c for c in df.columns if c.startswith(prefix + " B")][0]
    fo = [c for c in df.columns if c.startswith(prefix + " F")][0]
    return pd.to_numeric(df[b], errors="coerce"), pd.to_numeric(df[fo], errors="coerce")

res = {}
for rid, pre in ROWS.items():
    b, fu = getcols(pre)
    ok = b.notna() & fu.notna()           # paired participants only (assumption M6)
    b, fu = b[ok].astype(float), fu[ok].astype(float)
    d = fu - b                            # follow-up minus baseline (S4)
    if rid == "chair":
        # SRM on raw 10000 placeholders is meaningless: use participants able at both visits
        able = (b < 10000) & (fu < 10000)
        dd = d[able]
        wd = d                             # Wilcoxon with 10000 for rank (F2)
    else:
        dd, wd = d, d
    nz = wd[wd != 0]
    if len(nz) > 0:
        p = wilcoxon(wd, zero_method="wilcox", correction=False, method="approx").pvalue
    else:
        p = float("nan")
    srm = dd.mean() / dd.std(ddof=1)
    res[rid] = dict(med_b=b.median(), med_f=fu.median(), p=p, srm=srm)
    print(f"{rid:10s} n_pair={ok.sum():2d} n_B={getcols(pre)[0].notna().sum()} n_F={getcols(pre)[1].notna().sum()} "
          f"medB={b.median():.4g} medF={fu.median():.4g} p={p:.4g} SRM={srm:.4g}")

for key, cell in T["cells"].items():
    rid, c = key.split("|")
    v = res[rid][c]
    cell["value"] = None if v != v else float(v)
    cell["stars"] = "a" if (c == "p" and v == v and v < 0.05) else ""
    cell["source"] = "section: paired-row loop (median/wilcoxon/SRM)"
os.makedirs(out_dir, exist_ok=True)
json.dump(T, open(os.path.join(out_dir, "filled.json"), "w"), indent=1)
print("wrote filled.json")
