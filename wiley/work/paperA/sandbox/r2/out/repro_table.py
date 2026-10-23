"""Reproduce Table 1 (median change in functional assessments over 6 years).
Usage: python -I out/repro_table.py data out
"""
import sys, os, json, glob
import numpy as np
import pandas as pd
from scipy import stats

DATA_DIR, OUT_DIR = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(DATA_DIR)), "template.json")
UNABLE = 10000.0

ROWS = {  # row id -> (baseline column, follow-up column)
    "fvc_sit": ("FVC sitting B (%)", "FVC sitting F (%)"),
    "fvc_lie": ("FVC lying B (%)", "FVC lying F (%)"),
    "hip_flex": ("Hip flexion B (kg)", "Hip flexion F (kg)"),
    "hip_add": ("Hip Adduction B (kg)", "Hip Adduction F (kg)"),
    "hip_abd": ("Hip Abduction B (kg)", "Hip Abduction F (kg)"),
    "knee_ext": ("Knee Extension B (kg)", "Knee Extension F (kg)"),
    "knee_flex": ("Knee Flexion B (kg)", "Knee Flexion F (kg)"),
    "ankle_df": ("Ankle Dorsiflexion B (kg)", "Ankle Dorsiflexion F (kg)"),
    "smwt": ("Six minute walk B (m)", "Six minute walk F (m)"),
    "tug": ("Timed up and go velocity B (m/s)", "Timed up and go velocity F (m/s)"),
    "tmwr": ("Ten metre walk or run velocity B (m/s)", "Ten metre walk or run velocity F (m/s)"),
    "stair_up": ("Stair ascent velocity B (steps/s)", "Stair ascent velocity F (steps/s)"),
    "stair_down": ("Stair descent velocity B (steps/s)", "Stair descent velocity F (steps/s)"),
    "chair": ("Chair Rise B (s)", "Chair Rise F (s)"),
}


def load_data(data_dir):
    path = sorted(glob.glob(os.path.join(data_dir, "*.xlsx")))[0]
    df = pd.read_excel(path, sheet_name=0)
    # keep participant rows only (drop blank + NOTES rows)
    df = df[pd.to_numeric(df["Patient no"], errors="coerce").notna()].copy()
    print(f"Loaded {path}: {len(df)} participants")
    return df


def paired(df, b, f):
    sub = df[[b, f]].apply(pd.to_numeric, errors="coerce").dropna()
    return sub[b].to_numpy(float), sub[f].to_numpy(float)


def wilcoxon_spss(x_b, x_f):
    """SPSS-style asymptotic Wilcoxon signed-rank: zero diffs dropped, tie-corrected
    variance, no continuity correction, two-sided normal p."""
    d = x_f - x_b
    if np.all(d == 0):
        return float("nan"), float("nan")
    res = stats.wilcoxon(x_f, x_b, zero_method="wilcox", correction=False,
                         alternative="two-sided", method="approx")
    return float(res.pvalue), float(getattr(res, "zstatistic", np.nan))


def srm(x_b, x_f):
    d = x_f - x_b  # follow-up minus baseline (same convention as the dataset's Delta columns)
    return float(np.mean(d) / np.std(d, ddof=1))


def main():
    df = load_data(DATA_DIR)
    with open(TEMPLATE) as fh:
        out = json.load(fh)
    for rid, (b, f) in ROWS.items():
        xb, xf = paired(df, b, f)
        n = len(xb)
        med_b, med_f = float(np.median(xb)), float(np.median(xf))
        p, z = wilcoxon_spss(xb, xf)
        s = srm(xb, xf)
        n_unable = (int((xb >= UNABLE).sum()), int((xf >= UNABLE).sum()))
        extra = f" unable(B,F)={n_unable}" if rid == "chair" else ""
        print(f"{rid:10s} n={n:2d} medB={med_b:.4g} medF={med_f:.4g} z={z:.4f} p={p:.5g} SRM={s:.4f}{extra}")
        cells = out["cells"]
        cells[f"{rid}|med_b"].update(value=med_b, stars="", source="main: np.median over paired cases (baseline)")
        cells[f"{rid}|med_f"].update(value=med_f, stars="", source="main: np.median over paired cases (follow-up)")
        cells[f"{rid}|p"].update(value=p, stars="a" if p < 0.05 else "",
                                 source="wilcoxon_spss (scipy.stats.wilcoxon approx, no continuity corr.)")
        cells[f"{rid}|srm"].update(value=s, stars="", source="srm: mean(F-B)/SD(F-B, ddof=1)")
        for c in ("med_b", "med_f", "p", "srm"):
            cells[f"{rid}|{c}"]["n_paired"] = n

    # Sensitivity (logged only): chair rise restricted to participants with paired FVC sitting (n=17)
    sub = df[["FVC sitting B (%)", "FVC sitting F (%)", "Chair Rise B (s)", "Chair Rise F (s)"]].apply(
        pd.to_numeric, errors="coerce").dropna()
    xb, xf = sub["Chair Rise B (s)"].to_numpy(), sub["Chair Rise F (s)"].to_numpy()
    print(f"[sensitivity] chair restricted to FVC-sitting-paired n={len(xb)}: medB={np.median(xb):.4g} "
          f"medF={np.median(xf):.4g} p={wilcoxon_spss(xb, xf)[0]:.5g} SRM={srm(xb, xf):.4f}")
    # Sensitivity: exact Wilcoxon p for each row
    for rid, (b, f) in ROWS.items():
        xb, xf = paired(df, b, f)
        try:
            pe = stats.wilcoxon(xf, xb, zero_method="wilcox", method="exact").pvalue
        except Exception as e:
            pe = float("nan")
        print(f"[sensitivity] exact-ish Wilcoxon p {rid}: {pe:.5g}")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "filled.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("Wrote", os.path.join(OUT_DIR, "filled.json"))


if __name__ == "__main__":
    main()
