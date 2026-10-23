import sys, json, os, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
data_dir, out_dir = sys.argv[1], sys.argv[2]
d = pd.read_excel(os.path.join(data_dir, "repository_HFNC_x_NIV.xlsx"))
tmpl = json.load(open("template.json"))
G = {"niv": d[d.Gr == "NIV"], "hfnc": d[d.Gr == "HFNC"]}
N = {k: len(v) for k, v in G.items()}

def num(s): return pd.to_numeric(s, errors="coerce")
def chi(a, b, na, nb):  # a,b counts; 2x2 chi-square with Yates (R chisq.test default)
    t = np.array([[a, na - a], [b, nb - b]])
    return stats.chi2_contingency(t, correction=True)[1]
def wil(x, y):  # R wilcox.test default: normal approx w/ continuity correction when ties
    return stats.mannwhitneyu(x, y, alternative="two-sided", use_continuity=True, method="asymptotic").pvalue

def flag(df, rid):
    if rid == "female": return df.Gn == 1
    if rid == "pw": return df.PW == "y"
    if rid == "prh": return df.PRH == "y"
    if rid == "sed": return num(df.SDu).notna()      # numeric days => sedated; 'nc' => not sedated
    if rid == "atb": return df.ATB == "y"
    vm = {"v_rsv": "RSV", "v_bo": "Bo", "v_ad": "Ad", "v_sc": "SC", "v_pa": "Pa", "v_me": "Me", "v_re": "RE"}
    t = vm[rid]
    return df.VP.fillna("").apply(lambda s: t in [x.strip() for x in s.split(",")])
cont = {"dur": "TD", "fio2": "FiO2_0", "wdf": "WD_0", "spo2": "SpO2_0", "sed_d": "SDu", "ngt_d": "ETu", "imv_d": "MV", "pim": "PIM"}
nop = {k for k in ["v_rsv","v_bo","v_ad","v_sc","v_pa","v_me","v_re"]}

res = {}
for r in tmpl["rows"]:
    rid = r["id"]
    if rid in cont:
        x = {k: num(v[cont[rid]]).dropna() for k, v in G.items()}
        for k in x:
            q = x[k].quantile([.25, .5, .75])  # type 7
            res[f"{rid}|{k}_mean"] = x[k].mean(); res[f"{rid}|{k}_sd"] = x[k].std(ddof=1)
            res[f"{rid}|{k}_med"] = q[.5]; res[f"{rid}|{k}_q1"] = q[.25]; res[f"{rid}|{k}_q3"] = q[.75]
            print(rid, k, "n_valid", len(x[k]))
        res[f"{rid}|p"] = wil(x["niv"], x["hfnc"])
    else:
        c = {k: int(flag(v, rid).sum()) for k, v in G.items()}
        for k in c:
            res[f"{rid}|{k}_n"] = c[k]; res[f"{rid}|{k}_pct"] = 100 * c[k] / N[k]
        if rid not in nop: res[f"{rid}|p"] = chi(c["niv"], c["hfnc"], N["niv"], N["hfnc"])

for key, cell in tmpl["cells"].items():
    v = res[key]
    cell["value"] = float(v) if not isinstance(v, int) else v
    cell["stars"] = ""
    cell["source"] = "chi2_contingency(Yates) / mannwhitneyu(asymptotic, cc) / group summaries in repro_table.py"
    print(key, cell["value"])
json.dump(tmpl, open(os.path.join(out_dir, "filled.json"), "w"), indent=1)
