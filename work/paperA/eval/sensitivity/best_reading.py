"""Recompute the whole of Table 1 under the single reading that best matches the
published values, and compare every cell with the published table.
Reading: medians over all values available at each visit (10000 s kept for chair rise);
P = asymptotic Wilcoxon (zeros dropped, no continuity correction) on paired cases;
SRM = mean(F-B)/SD(F-B, n-1), with the velocity rows including participant 20 whose
blank baseline is treated as 0 (as a spreadsheet subtraction would); half-even rounding.
Also: jitter test for myometry P values (deposited to 0.1 kg).
Usage: python -I best_reading.py <path to xlsx>
"""
import sys
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
import numpy as np, pandas as pd
from scipy import stats

df = pd.read_excel(sys.argv[1], header=0)
df = df[pd.to_numeric(df['Patient no'], errors='coerce').notna()].copy()
df.columns = [str(c).strip() for c in df.columns]
ROWS = {
 'fvc_sit': ('FVC sitting B (%)', 'FVC sitting F (%)', (77, 64, 0.001, -1.29), 0),
 'fvc_lie': ('FVC lying B (%)', 'FVC lying F (%)', (70, 54, 0.002, -1.06), 0),
 'hip_flex': ('Hip flexion B (kg)', 'Hip flexion F (kg)', (7.7, 6.4, 0.13, -0.35), 1),
 'hip_add': ('Hip Adduction B (kg)', 'Hip Adduction F (kg)', (6.1, 4.2, 0.02, -0.59), 1),
 'hip_abd': ('Hip Abduction B (kg)', 'Hip Abduction F (kg)', (8.3, 7.2, 0.76, -0.01), 1),
 'knee_ext': ('Knee Extension B (kg)', 'Knee Extension F (kg)', (11.1, 12.0, 0.15, -0.26), 1),
 'knee_flex': ('Knee Flexion B (kg)', 'Knee Flexion F (kg)', (8.4, 4.8, 0.21, -0.12), 1),
 'ankle_df': ('Ankle Dorsiflexion B (kg)', 'Ankle Dorsiflexion F (kg)', (14.7, 13.9, 0.07, -0.42), 1),
 'smwt': ('Six minute walk B (m)', 'Six minute walk F (m)', (391, 286, 0.001, -0.85), 0),
 'tug': ('Timed up and go velocity B (m/s)', 'Timed up and go velocity F (m/s)', (0.5, 0.3, 0.007, -0.48), 1),
 'tmwr': ('Ten metre walk or run velocity B (m/s)', 'Ten metre walk or run velocity F (m/s)', (1.2, 0.8, '<0.001', -1.02), 1),
 'stair_up': ('Stair ascent velocity B (steps/s)', 'Stair ascent velocity F (steps/s)', (0.7, 0.4, 0.001, -0.46), 1),
 'stair_down': ('Stair descent velocity B (steps/s)', 'Stair descent velocity F (steps/s)', (1.2, 0.4, 0.008, -0.47), 1),
 'chair': ('Chair Rise B (s)', 'Chair Rise F (s)', (2.6, 9.8, 0.001, 'N/A'), 1),
}
VEL = {'tug', 'tmwr', 'stair_up', 'stair_down'}


def num(c):
    return pd.to_numeric(df[c], errors='coerce').values


def r(x, d, mode=ROUND_HALF_EVEN):
    return float(Decimal(repr(round(float(x), 10))).quantize(Decimal(1).scaleb(-d), rounding=mode))


def fmt_p(p):
    # paper style: 3 dp below 0.01, 2 dp otherwise; '<0.001' when 3 dp rounds to 0
    if r(p, 3) == 0:
        return '<0.001'
    return f"{r(p, 3):.3f}" if p < 0.0095 else f"{r(p, 2):.2f}"


n_match = n_total = 0
print(f"{'row':11}{'med_b':>16}{'med_f':>16}{'P':>22}{'SRM':>22}")
for rid, (cb, cf, pub, dp) in ROWS.items():
    b, f = num(cb), num(cf)
    ok = ~np.isnan(b) & ~np.isnan(f)
    mb, mf = r(np.median(b[~np.isnan(b)]), dp), r(np.median(f[~np.isnan(f)]), dp)
    p = stats.wilcoxon(f[ok], b[ok], zero_method='wilcox', correction=False, method='approx').pvalue
    if rid in VEL:
        bb = np.where(np.isnan(b), 0.0, b); d = f - bb; d = d[~np.isnan(d)]
    else:
        d = (f - b)[ok]
    s = 'N/A' if rid == 'chair' else r(d.mean() / d.std(ddof=1), 2)
    got = (mb, mf, fmt_p(p), s)
    pubs = (pub[0], pub[1], pub[2] if isinstance(pub[2], str) else (f"{pub[2]:.3f}" if pub[2] < 0.0095 else f"{pub[2]:.2f}"), pub[3])
    cells = []
    for g, q in zip(got, pubs):
        m = (str(g) == str(q)) or (not isinstance(g, str) and not isinstance(q, str) and abs(float(g) - float(q)) < 1e-9)
        n_match += m; n_total += 1
        cells.append(f"{g}/{q}{'' if m else ' X'}")
    print(f"{rid:11}" + ''.join(f"{c:>16}" if i < 2 else f"{c:>22}" for i, c in enumerate(cells)))
print(f"Cells matching published exactly after rounding: {n_match}/{n_total}")

print('\nRounding note: chair baseline median 2.65 -> half-even', r(2.65, 1), '; half-up', r(2.65, 1, ROUND_HALF_UP))

print('\n=== Jitter test for myometry P (values deposited to 0.1 kg; jitter U(-0.05, 0.05)) ===')
rng = np.random.default_rng(2)
for rid in ['hip_flex', 'knee_ext']:
    cb, cf, pub, dp = ROWS[rid]
    b, f = num(cb), num(cf)
    ps = np.array([stats.wilcoxon(f + rng.uniform(-.05, .05, len(f)), b + rng.uniform(-.05, .05, len(b)),
                                  correction=False, method='approx').pvalue for _ in range(3000)])
    print(f"{rid:9} pub={pub[2]} jittered P 1st/50th/99th pct = {np.percentile(ps, 1):.4f}/{np.median(ps):.4f}/{np.percentile(ps, 99):.4f}; "
          f"share rounding to published = {np.mean(np.round(ps, 2) == pub[2]):.3f}")
