"""Sensitivity analyses for Paper A Table 1 non-A cells.
Usage: python -I sens_all.py <path to xlsx>
"""
import sys
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
import numpy as np, pandas as pd
from scipy import stats

df = pd.read_excel(sys.argv[1], header=0)
df = df[pd.to_numeric(df['Patient no'], errors='coerce').notna()].copy()
df.columns = [str(c).strip() for c in df.columns]
U = 10000.0
ROWS = {
 'fvc_sit': ('FVC sitting B (%)', 'FVC sitting F (%)'),
 'fvc_lie': ('FVC lying B (%)', 'FVC lying F (%)'),
 'hip_flex': ('Hip flexion B (kg)', 'Hip flexion F (kg)'),
 'hip_add': ('Hip Adduction B (kg)', 'Hip Adduction F (kg)'),
 'hip_abd': ('Hip Abduction B (kg)', 'Hip Abduction F (kg)'),
 'knee_ext': ('Knee Extension B (kg)', 'Knee Extension F (kg)'),
 'knee_flex': ('Knee Flexion B (kg)', 'Knee Flexion F (kg)'),
 'ankle_df': ('Ankle Dorsiflexion B (kg)', 'Ankle Dorsiflexion F (kg)'),
 'smwt': ('Six minute walk B (m)', 'Six minute walk F (m)'),
 'tug': ('Timed up and go velocity B (m/s)', 'Timed up and go velocity F (m/s)'),
 'tmwr': ('Ten metre walk or run velocity B (m/s)', 'Ten metre walk or run velocity F (m/s)'),
 'stair_up': ('Stair ascent velocity B (steps/s)', 'Stair ascent velocity F (steps/s)'),
 'stair_down': ('Stair descent velocity B (steps/s)', 'Stair descent velocity F (steps/s)'),
 'chair': ('Chair Rise B (s)', 'Chair Rise F (s)'),
}
PUB = {'fvc_sit': (77, 64, 0.001, -1.29), 'fvc_lie': (70, 54, 0.002, -1.06), 'hip_flex': (7.7, 6.4, 0.13, -0.35),
 'hip_add': (6.1, 4.2, 0.02, -0.59), 'hip_abd': (8.3, 7.2, 0.76, -0.01), 'knee_ext': (11.1, 12.0, 0.15, -0.26),
 'knee_flex': (8.4, 4.8, 0.21, -0.12), 'ankle_df': (14.7, 13.9, 0.07, -0.42), 'smwt': (391, 286, 0.001, -0.85),
 'tug': (0.5, 0.3, 0.007, -0.48), 'tmwr': (1.2, 0.8, '<0.001', -1.02), 'stair_up': (0.7, 0.4, 0.001, -0.46),
 'stair_down': (1.2, 0.4, 0.008, -0.47), 'chair': (2.6, 9.8, 0.001, 'N/A')}
DIST = {'tug': 6.0, 'tmwr': 10.0, 'stair_up': 4.0, 'stair_down': 4.0}


def num(c):
    return pd.to_numeric(df[c], errors='coerce')


def paired(b, f):
    s = pd.DataFrame({'b': num(b), 'f': num(f)}).dropna()
    return s['b'].values, s['f'].values


def rnd(x, d, mode):
    q = Decimal(1).scaleb(-d)
    return float(Decimal(repr(round(x, 10))).quantize(q, rounding=mode))


def srm(b, f, ddof=1):
    d = f - b
    return d.mean() / d.std(ddof=ddof)


def wvariants(b, f):
    out = {}
    for zm in ('wilcox', 'pratt', 'zsplit'):
        for cc in (False, True):
            try:
                out[f'approx/{zm}/cc={int(cc)}'] = stats.wilcoxon(f, b, zero_method=zm, correction=cc, method='approx').pvalue
            except Exception:
                out[f'approx/{zm}/cc={int(cc)}'] = float('nan')
    try:
        out['exact/wilcox'] = stats.wilcoxon(f, b, zero_method='wilcox', method='exact').pvalue
    except Exception:
        out['exact/wilcox'] = float('nan')
    return out


print('=== 1. Medians: paired-only vs all available values at each visit ===')
print(f"{'row':11}{'pub_b':>7}{'pair_b':>9}{'all_b':>9}{'n_all_b':>8}{'pub_f':>7}{'pair_f':>9}{'all_f':>9}{'n_all_f':>8}")
for r, (b, f) in ROWS.items():
    pb, pf = paired(b, f)
    ab, af = num(b).dropna().values, num(f).dropna().values
    print(f"{r:11}{PUB[r][0]:>7}{np.median(pb):>9.4g}{np.median(ab):>9.4g}{len(ab):>8}{PUB[r][1]:>7}{np.median(pf):>9.4g}{np.median(af):>9.4g}{len(af):>8}")

print('\n=== 2. Rounding of chair baseline 2.65 and FVC lying baseline 70.5 ===')
for x, d in [(2.65, 1), (70.5, 0), (float(np.median(paired(*ROWS['chair'])[0])), 1)]:
    print(f"x={x!r}: half-up={rnd(x, d, ROUND_HALF_UP)} half-even={rnd(x, d, ROUND_HALF_EVEN)} python round(float)={round(x, d)}")

print('\n=== 3. Chair rise subsets, aiming at footnote n=17 ===')
cb, cf = num(ROWS['chair'][0]), num(ROWS['chair'][1])
fs = num('FVC sitting B (%)').notna() & num('FVC sitting F (%)').notna()
sets = {
    'paired (n=22)': cb.notna() & cf.notna(),
    'paired, both finite': cb.notna() & cf.notna() & (cb < U) & (cf < U),
    'paired, finite at baseline': cb.notna() & cf.notna() & (cb < U),
    'paired, FVC-sitting-paired': cb.notna() & cf.notna() & fs,
}
for k, m in sets.items():
    b, f = cb[m].values, cf[m].values
    p = stats.wilcoxon(f, b, zero_method='wilcox', correction=False, method='approx').pvalue
    print(f"{k:30} n={int(m.sum()):2d} medB={np.median(b):.4g} medF={np.median(f):.4g} p={p:.4g}")
print('Finite-only medians (unable dropped): B n=%d %.4g, F n=%d %.4g' % ((cb < U).sum(), np.median(cb[cb < U]), (cf < U).sum(), np.median(cf[cf < U])))
print('All available incl. 10000: B n=%d %.4g, F n=%d %.4g' % (cb.notna().sum(), np.median(cb.dropna()), cf.notna().sum(), np.median(cf.dropna())))
print('Sorted chair F (all 23):', sorted(cf.dropna().tolist()))

print('\n=== 4. Wilcoxon variants (paired data as deposited) ===')
for r in ROWS:
    b, f = paired(*ROWS[r])
    v = wvariants(b, f)
    nz = int((f - b != 0).sum())
    print(f"{r:11} pub={PUB[r][2]!s:7} n={len(b)} nonzero={nz} " + ' '.join(f"{k}={x:.4f}" for k, x in v.items()))

print('\n=== 5. Timed tests re-expressed as times (dist/velocity; 0 velocity -> 10000 s) ===')
for r in DIST:
    b, f = paired(*ROWS[r])
    tb = np.where(b > 0, DIST[r] / np.where(b > 0, b, 1), U)
    tf = np.where(f > 0, DIST[r] / np.where(f > 0, f, 1), U)
    v = wvariants(tb, tf)
    print(f"{r:11} pub={PUB[r][2]!s:7} " + ' '.join(f"{k}={x:.4f}" for k, x in v.items()))

print('\n=== 6. SRM variants ===')
for r in ['tug', 'tmwr', 'stair_up', 'stair_down', 'fvc_sit', 'fvc_lie', 'smwt', 'hip_add']:
    b, f = paired(*ROWS[r])
    nz = (b > 0) | (f > 0)
    line = f"{r:11} pub={PUB[r][3]:>6} ddof1={srm(b, f):.4f} ddof0={srm(b, f, 0):.4f}"
    line += f" excl_both0(n={int(nz.sum())})={srm(b[nz], f[nz]):.4f}"
    if r in DIST:
        able = (b > 0) & (f > 0)
        line += f" both_able(n={int(able.sum())})={srm(b[able], f[able]):.4f}"
        bb, ff = num(ROWS[r][0]).fillna(0).values, num(ROWS[r][1]).values
        line += f" n23_pt20_B=0:{srm(bb, ff):.4f}"
    print(line)
d10 = num('Delta 10m walk or run velocity (m/s)').dropna().values
print(f"tmwr from deposited Delta column: n={len(d10)} SRM={d10.mean() / d10.std(ddof=1):.4f} (ddof0 {d10.mean() / d10.std(ddof=0):.4f})")
x = (num(ROWS['tmwr'][1]) - num(ROWS['tmwr'][0])).values
y = num('Delta 10m walk or run velocity (m/s)').values
mm = [(int(p), xi, yi) for p, xi, yi in zip(df['Patient no'], x, y) if not (np.isnan(xi) and np.isnan(yi)) and (np.isnan(xi) or np.isnan(yi) or abs(xi - yi) > 1e-6)]
print('tmwr F-B vs Delta column mismatches (patient, F-B, Delta):', mm)
d6 = num('Delta Six Minute Walk (m)').dropna().values
print(f"smwt from Delta column: n={len(d6)} SRM={d6.mean() / d6.std(ddof=1):.4f}")
b, f = paired(*ROWS['tmwr'])
loo = [srm(np.delete(b, i), np.delete(f, i)) for i in range(len(b))]
print('tmwr leave-one-out SRM range:', round(min(loo), 4), round(max(loo), 4))
