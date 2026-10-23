"""Reproduce Table 1 (demographic and clinical characteristics), HFNC vs NIV.
Usage: python -I repro_table.py <data_dir> <out_dir>"""
import sys, os, re, json
import numpy as np, pandas as pd
from scipy import stats

DATA, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "template.json")
GROUPS = {"niv": "NIV", "hfnc": "HFNC"}


def load():
    df = pd.read_excel(os.path.join(DATA, "repository_HFNC_x_NIV.xlsx"))
    assert len(df) == 252 and (df.Gr.value_counts() == 126).all()
    return df


def num(s):
    """Numeric parse; codes 'md'/'nc' -> NaN; '17h' -> 17."""
    s = s.astype(str).str.strip().str.replace(r"h$", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


# ---------------- summaries ----------------
def binary_summary(df, flag):
    """flag: Series of 1/0/NaN. N and % (denominator = whole group, 126); p = chi-square
    with Yates' correction (R chisq.test default) on complete cases."""
    res = {}
    for g, lab in GROUPS.items():
        f = flag[df.Gr == lab]
        n = int((f == 1).sum())
        res[f"{g}_n"] = n
        res[f"{g}_pct"] = 100.0 * n / len(f)
    ok = flag.notna()
    tab = pd.crosstab(df.Gr[ok], flag[ok])
    res["p"] = float(stats.chi2_contingency(tab.values, correction=True)[1])
    return res


def mw_p(x, y):
    """R wilcox.test default with ties: normal approximation with continuity correction,
    tie-corrected variance."""
    return float(stats.mannwhitneyu(x, y, alternative="two-sided", method="asymptotic",
                                    use_continuity=True).pvalue)


def mean_sd_summary(df, v):
    res, xs = {}, {}
    for g, lab in GROUPS.items():
        x = v[df.Gr == lab].dropna()
        xs[g] = x.values
        res[f"{g}_mean"] = float(x.mean())
        res[f"{g}_sd"] = float(x.std(ddof=1))
    res["p"] = mw_p(xs["niv"], xs["hfnc"])
    return res


def median_iqr_summary(df, v):
    res, xs = {}, {}
    for g, lab in GROUPS.items():
        x = v[df.Gr == lab].dropna()
        xs[g] = x.values
        res[f"{g}_med"] = float(np.median(x))
        # R quantile type 7 == numpy 'linear'
        res[f"{g}_q1"] = float(np.quantile(x, 0.25, method="linear"))
        res[f"{g}_q3"] = float(np.quantile(x, 0.75, method="linear"))
    res["p"] = mw_p(xs["niv"], xs["hfnc"])
    return res


def yn(s):
    return s.astype(str).str.strip().map({"y": 1.0, "n": 0.0})  # 'md' -> NaN


def virus_summary(df, code):
    """Count patients whose viral panel contains the code; % of whole group. No p in table."""
    toks = df.VP.fillna("").astype(str).apply(lambda s: [t.strip() for t in str(s).split(",")])
    flag = toks.apply(lambda t: code in t).astype(float)
    flag[df.VP.isna()] = np.nan  # sample not available
    res = {}
    for g, lab in GROUPS.items():
        f = flag[df.Gr == lab]
        n = int((f == 1).sum())
        res[f"{g}_n"] = n
        res[f"{g}_pct"] = 100.0 * n / len(f)
    return res


def build(df):
    rows = {}
    rows["female"] = (binary_summary(df, df.Gn.astype(float)), "binary_summary(Gn==1)")
    rows["pw"] = (binary_summary(df, yn(df.PW)), "binary_summary(PW=='y')")
    rows["prh"] = (binary_summary(df, yn(df.PRH)), "binary_summary(PRH=='y')")
    rows["dur"] = (median_iqr_summary(df, num(df.TD)), "median_iqr_summary(TD)")
    rows["fio2"] = (mean_sd_summary(df, num(df.FiO2_0)), "mean_sd_summary(FiO2_0)")
    rows["wdf"] = (mean_sd_summary(df, num(df.WD_0)), "mean_sd_summary(WD_0)")
    rows["spo2"] = (mean_sd_summary(df, num(df.SpO2_0)), "mean_sd_summary(SpO2_0)")
    sdu = num(df.SDu)
    rows["sed"] = (binary_summary(df, sdu.notna().astype(float)), "binary_summary(SDu recorded, i.e. not 'nc')")
    rows["sed_d"] = (median_iqr_summary(df, sdu), "median_iqr_summary(SDu, sedated only)")
    rows["ngt_d"] = (median_iqr_summary(df, num(df.ETu)), "median_iqr_summary(ETu, tube users only)")
    rows["imv_d"] = (median_iqr_summary(df, num(df.MV)), "median_iqr_summary(MV, ventilated only)")
    rows["atb"] = (binary_summary(df, yn(df.ATB)), "binary_summary(ATB=='y')")
    rows["pim"] = (mean_sd_summary(df, num(df.PIM)), "mean_sd_summary(PIM)")
    for rid, code in [("v_rsv", "RSV"), ("v_bo", "Bo"), ("v_ad", "Ad"), ("v_sc", "SC"),
                      ("v_pa", "Pa"), ("v_me", "Me"), ("v_re", "RE")]:
        rows[rid] = (virus_summary(df, code), f"virus_summary(VP contains '{code}')")
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load()
    with open(TEMPLATE, encoding="utf-8") as fh:
        tpl = json.load(fh)
    rows = build(df)
    for key, cell in tpl["cells"].items():
        rid, col = key.split("|")
        vals, src = rows[rid]
        cell["value"] = vals[col]
        cell["stars"] = ""
        cell["source"] = src
    with open(os.path.join(OUT, "filled.json"), "w", encoding="utf-8") as fh:
        json.dump(tpl, fh, indent=1)
    for rid, (vals, src) in rows.items():
        print(f"{rid:7s}", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in vals.items()})
    missing = [k for k, c in tpl["cells"].items() if c["value"] is None]
    print("cells:", len(tpl["cells"]), "unfilled:", missing)


if __name__ == "__main__":
    main()
