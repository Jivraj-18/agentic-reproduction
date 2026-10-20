"""Extra sensitivity checks: participant-20 handling, leave-one-out P values,
and rounding perturbation of deposited velocities.
Usage: python -I sens_extra.py <path to xlsx>
"""
import sys
import numpy as np, pandas as pd
from scipy import stats

df = pd.read_excel(sys.argv[1], header=0)
df = df[pd.to_numeric(df['Patient no'], errors='coerce').notna()].copy()
df.columns = [str(c).strip() for c in df.columns]
pid = df['Patient no'].astype(int).values
ROWS = {
 'hip_flex': ('Hip flexion B (kg)', 'Hip flexion F (kg)', 0.13),
 'knee_ext': ('Knee Extension B (kg)', 'Knee Extension F (kg)', 0.15),
 'tug': ('Timed up and go velocity B (m/s)', 'Timed up and go velocity F (m/s)', 0.007),
 'tmwr': ('Ten metre walk or run velocity B (m/s)', 'Ten metre walk or run velocity F (m/s)', 0.0005),
 'stair_up': ('Stair ascent velocity B (steps/s)', 'Stair ascent velocity F (steps/s)', 0.001),
 'stair_down': ('Stair descent velocity B (steps/s)', 'Stair descent velocity F (steps/s)', 0.008),
}


def num(c):
    return pd.to_numeric(df[c], errors='coerce').values


def wp(b, f, zm='wilcox', cc=False):
    return stats.wilcoxon(f, b, zero_method=zm, correction=cc, method='approx').pvalue


def srm(b, f):
    d = f - b
    return d.mean() / d.std(ddof=1)


print('=== A. Velocity rows with participant 20 baseline set to 0 (n=23) ===')
for r in ['tug', 'tmwr', 'stair_up', 'stair_down']:
    b, f = num(ROWS[r][0]), num(ROWS[r][1])
    b0 = np.where(np.isnan(b), 0.0, b)
    print(f"{r:11} medB={np.median(b0):.4g} medF={np.median(f):.4g} p_wilcox={wp(b0, f):.4f} p_pratt={wp(b0, f, 'pratt'):.4f} SRM={srm(b0, f):.4f}")

print('\n=== B. Leave-one-out asymptotic Wilcoxon P (which single exclusion hits the published value?) ===')
for r, (cb, cf, pub) in ROWS.items():
    b, f = num(cb), num(cf)
    ok = ~np.isnan(b) & ~np.isnan(f)
    b, f, ids = b[ok], f[ok], pid[ok]
    res = [(int(ids[i]), wp(np.delete(b, i), np.delete(f, i))) for i in range(len(b))]
    lo, hi = min(x for _, x in res), max(x for _, x in res)
    near = [(i, round(x, 4)) for i, x in res if round(x, 3 if pub < 0.1 else 2) == pub]
    print(f"{r:11} pub={pub} LOO range {lo:.4f}-{hi:.4f}; exclusions that round to published: {near}")

print('\n=== C. Rounding perturbation: velocities deposited to 2 dp; jitter non-zero values by U(-0.005, 0.005) ===')
rng = np.random.default_rng(1)
for r in ['tug', 'stair_down', 'stair_up']:
    cb, cf, pub = ROWS[r]
    b, f = num(cb), num(cf)
    ok = ~np.isnan(b) & ~np.isnan(f)
    b, f = b[ok], f[ok]
    ps = []
    for _ in range(5000):
        bj = np.where(b > 0, b + rng.uniform(-0.005, 0.005, len(b)), 0.0)
        fj = np.where(f > 0, f + rng.uniform(-0.005, 0.005, len(f)), 0.0)
        ps.append(wp(bj, fj))
    ps = np.array(ps)
    print(f"{r:11} pub={pub} jittered P: 1st pct {np.percentile(ps, 1):.4f}, median {np.median(ps):.4f}, 99th pct {np.percentile(ps, 99):.4f}; "
          f"share rounding to published = {np.mean(np.round(ps, 3) == pub):.3f}")

print('\n=== D. Myometry rows: exclude participant 20 (no baseline timed data) ===')
for r in ['hip_flex', 'knee_ext']:
    cb, cf, pub = ROWS[r]
    b, f = num(cb), num(cf)
    m = pid != 20
    print(f"{r:11} pub={pub} p(n=22, no pt20)={wp(b[m], f[m]):.4f}")

print('\n=== E. TUG differences (F-B) for inspection ===')
b, f = num(ROWS['tug'][0]), num(ROWS['tug'][1])
print(sorted([(round(float(x), 2), int(i)) for x, i in zip(f - b, pid) if not np.isnan(x)]))
