"""Reproduce Table 1 (knot-tying techniques) from the deposited data.

Usage: python -I repro_table.py <data_dir> <out_dir>
"""
import sys, os, json, glob, warnings
import numpy as np
import pandas as pd
from scipy import stats, optimize
import statsmodels.api as sm

warnings.filterwarnings("ignore")
DATA, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(DATA)), "template.json")

TECHS = ["A", "B", "C"]          # A intracorporeal, B open pusher, C closed pusher
CONTRASTS = {"io": ("A", "B"), "ic": ("A", "C"), "oc": ("B", "C")}


# ---------------------------------------------------------------- load_data
def mmss_to_sec(s):
    if pd.isna(s):
        return np.nan
    sec = 0.0
    for p in str(s).strip().split(":"):
        sec = sec * 60 + float(p)
    return sec


def load_data():
    f = glob.glob(os.path.join(DATA, "*.xlsx"))[0]
    d = pd.read_excel(f, sheet_name="Knot-Tying_Data")
    d = d.rename(columns={"knot-tying technique": "tech",
                          "delta knot strength (mm)": "ks",
                          "knot spread ability (mm)": "sp"})
    d["time"] = d["time total (s)"].map(mmss_to_sec)
    d["subject"] = d["subject"].astype(str)
    d["run"] = d["run"].astype(int)
    # A run with knot length before/after both 0 is a failed knot (no loop to measure):
    # its knot strength and spread values are treated as not measured (see assumptions.md).
    failed = (d["knot strength before 15 N(mm)"] == 0) & (d["knot strength after 15 N (mm)"] == 0)
    print(f"failed-knot rows with all-zero measurements set to missing for ks/sp: {int(failed.sum())}")
    d.loc[failed, ["ks", "sp"]] = np.nan
    d["mi"] = (d["mistakes"] >= 1).astype(float)
    d.loc[d["mistakes"].isna(), "mi"] = np.nan
    for v in ["time", "ks", "sp", "mi"]:
        print(f"valid runs for {v}: {d[v].notna().sum()} (subjects {d.loc[d[v].notna(),'subject'].nunique()})")
    return d


# ---------------------------------------------------------------- design / emm
def design(df):
    """Treatment coding: intercept, tech B, tech C, run 2, run 3."""
    return np.column_stack([np.ones(len(df)),
                            (df.tech == "B").astype(float), (df.tech == "C").astype(float),
                            (df.run == 2).astype(float), (df.run == 3).astype(float)])


def emm_L(tech):
    """Estimated marginal mean (link scale) of a technique, averaging run effects equally
    (emmeans default)."""
    return np.array([1.0, tech == "B", tech == "C", 1 / 3, 1 / 3], dtype=float)


# ------------------------------------------------------- lmm_random_intercept
def lmm_random_intercept(d, var, log):
    df = d.dropna(subset=[var]).copy()
    y = np.log(df[var].astype(float).values) if log else df[var].astype(float).values
    m = sm.MixedLM(y, design(df), groups=df["subject"].values).fit(
        reml=True, method=["bfgs", "powell", "nm"])
    beta = np.asarray(m.fe_params)
    V = np.asarray(m.cov_params())[:len(beta), :len(beta)]
    # within-subject residual df for the t reference (technique varies within subject)
    n, p, g = len(df), len(beta), df.subject.nunique()
    dof = n - p - (g - 1)
    print(f"[{var}] LMM n={n} subjects={g} log={log} REML; beta={np.round(beta, 5)}; "
          f"sigma2_u={float(np.asarray(m.cov_re)[0, 0]):.5f} sigma2_e={m.scale:.5f}; df={dof}; "
          f"converged={m.converged}")
    return beta, V, dof


# ------------------------------------------------------------ glmm_logit
def glmm_logit(d, var, nagq=1):
    """Random-intercept logistic GLMM by ML with adaptive Gauss-Hermite quadrature
    (nAGQ=1 == Laplace approximation, lme4::glmer default)."""
    df = d.dropna(subset=[var]).copy()
    X = design(df)
    y = df[var].values
    groups = pd.factorize(df["subject"])[0]
    idx = [np.where(groups == k)[0] for k in range(groups.max() + 1)]
    gh_x, gh_w = np.polynomial.hermite.hermgauss(nagq)

    def negll(theta):
        beta, s = theta[:-1], np.exp(theta[-1])
        eta_all = X @ beta
        tot = 0.0
        for ix in idx:
            eta, yk = eta_all[ix], y[ix]
            b = 0.0
            for _ in range(100):  # Newton for the conditional mode
                pr = 1 / (1 + np.exp(-(eta + b)))
                step = (np.sum(yk - pr) - b / s**2) / (-np.sum(pr * (1 - pr)) - 1 / s**2)
                b -= step
                if abs(step) < 1e-12:
                    break
            pr = 1 / (1 + np.exp(-(eta + b)))
            sd = 1 / np.sqrt(np.sum(pr * (1 - pr)) + 1 / s**2)
            vals = []
            for xk, wk in zip(gh_x, gh_w):
                bb = b + np.sqrt(2) * sd * xk
                e = eta + bb
                vals.append(np.log(wk) + xk**2 + np.sum(yk * e - np.logaddexp(0, e))
                            - bb**2 / (2 * s**2))
            vals = np.array(vals)
            mx = vals.max()
            tot += mx + np.log(np.sum(np.exp(vals - mx))) + np.log(np.sqrt(2) * sd) \
                - 0.5 * np.log(2 * np.pi * s**2)
        return -tot

    start = np.zeros(X.shape[1] + 1)
    start[0] = np.log(y.mean() / (1 - y.mean()))
    res = optimize.minimize(negll, start, method="BFGS", options={"gtol": 1e-8})
    res = optimize.minimize(negll, res.x, method="Nelder-Mead",
                            options={"xatol": 1e-10, "fatol": 1e-12, "maxiter": 40000})
    theta = res.x
    k = len(theta)
    H = np.zeros((k, k))
    h = 1e-4
    for i in range(k):
        for j in range(i, k):
            ei = np.zeros(k); ej = np.zeros(k)
            ei[i] = h; ej[j] = h
            H[i, j] = H[j, i] = (negll(theta + ei + ej) - negll(theta + ei - ej)
                                 - negll(theta - ei + ej) + negll(theta - ei - ej)) / (4 * h * h)
    V = np.linalg.inv(H)[:-1, :-1]
    beta = theta[:-1]
    print(f"[{var}] GLMM logit nAGQ={nagq} n={len(df)} subjects={len(idx)}; beta={np.round(beta, 5)}; "
          f"sd_u={np.exp(theta[-1]):.5f}; -2logLik={2 * res.fun:.4f}; converged={res.success}")
    return beta, V


# ------------------------------------------------------------------ contrast
def contrast(beta, V, t1, t2, dof=None):
    L = emm_L(t1) - emm_L(t2)
    est = float(L @ beta)
    se = float(np.sqrt(L @ V @ L))
    if dof is None:
        q, p = stats.norm.ppf(0.975), 2 * stats.norm.sf(abs(est / se))
    else:
        q, p = stats.t.ppf(0.975, dof), 2 * stats.t.sf(abs(est / se), dof)
    return est, est - q * se, est + q * se, p


def main():
    d = load_data()
    with open(TEMPLATE) as fh:
        tpl = json.load(fh)
    cells = tpl["cells"]

    def put(key, val, src, unit=None):
        c = cells[key]
        c["value"] = float(val)
        c["stars"] = ""
        c["source"] = src
        if unit is not None:
            c["unit"] = unit

    specs = [("time", "lmm", True), ("ks", "lmm", True), ("sp", "lmm", False), ("mi", "glmm", None)]
    for var, kind, log in specs:
        if kind == "lmm":
            beta, V, dof = lmm_random_intercept(d, var, log)
            src = f"lmm_random_intercept({var}, log={log}) + contrast()"
        else:
            beta, V = glmm_logit(d, var, nagq=1)
            dof = None
            src = "glmm_logit(mi, Laplace) + contrast()"
        msrc = src.replace("contrast()", "emm_L() estimated marginal mean, back-transformed")
        for cid, (t1, t2) in CONTRASTS.items():
            est, lo, hi, p = contrast(beta, V, t1, t2, dof)
            e1, e2 = float(emm_L(t1) @ beta), float(emm_L(t2) @ beta)
            munit = None
            if kind == "glmm":
                est, lo, hi = np.exp(est), np.exp(lo), np.exp(hi)
                e1, e2 = 1 / (1 + np.exp(-e1)), 1 / (1 + np.exp(-e2))
                munit = "probability of >=1 mistake per run"
            elif log:
                est, lo, hi = np.exp(est), np.exp(lo), np.exp(hi)
                e1, e2 = np.exp(e1), np.exp(e2)
            k = f"{var}_{cid}"
            put(f"{k}|eff", est, src)
            put(f"{k}|lo", lo, src)
            put(f"{k}|hi", hi, src)
            put(f"{k}|p", p, src)
            put(f"{k}|m1", e1, msrc, munit)
            put(f"{k}|m2", e2, msrc, munit)
            print(f"{k}: eff={est:.5g} [{lo:.5g}, {hi:.5g}] p={p:.5g}  means ({e1:.5g}, {e2:.5g})")

    print("\nDescriptive arithmetic means over valid runs (reference only, not in table):")
    for var in ["time", "ks", "sp", "mi", "mistakes"]:
        print(" ", var, d.groupby("tech")[var].mean().round(4).to_dict())
    print("Descriptive geometric means (reference only):")
    for var in ["time", "ks"]:
        print(" ", var, d.groupby("tech")[var].apply(lambda x: np.exp(np.log(x.dropna()).mean())).round(4).to_dict())

    with open(os.path.join(OUT, "filled.json"), "w") as fh:
        json.dump(tpl, fh, indent=1)
    print("wrote", os.path.join(OUT, "filled.json"))


if __name__ == "__main__":
    main()
