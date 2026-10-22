"""Side check: at 45 min, M2CA-4NBB (test 1) is the test whose fit differs most between the runs and the
authors' supplement. Evaluate r2 of both parameter sets on the deposited raw data (Eq. 1/2, max=100)."""
import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.abspath(os.path.join(HERE, '..', '..'))
d = pd.read_csv(os.path.join(P, 'sandbox', 'r_opus', 'data', 'raw_crc.csv'))
def model(x, ec50, h, s):
    xb = ec50 * 10 ** ((1 / h) * np.log10(2 ** (1 / s) - 1)); return 100 / (1 + (xb / x) ** h) ** s
for combo in ('M2CA-4NBB', 'M2CA-EUG'):
    g = d[(d.combination == combo) & (d.test == 1) & (d.time_min == 45)].dropna(subset=['effect_pct'])
    x, y = g.conc_A_uM.values.astype(float), g.effect_pct.values.astype(float)
    f = pd.read_csv(os.path.join(P, 'sandbox', 'r_opus', 'out', 'per_test_fits.csv')).set_index('test').loc[combo + ':A']
    sets = {'run (opus)': (f.ec50_45, f.slope_45, f.s_45)}
    sets['authors'] = {'M2CA-4NBB': (2.4448, 1.6886, 0.5860), 'M2CA-EUG': (2.7703, 1.7176, 0.4632)}[combo]
    for lab, (e, h, s) in sets.items():
        if h is None: continue
        r = y - model(x, e, h, s); print(f'{combo} {lab}: EC50={e:.4f} slope={h:.4f} s={s:.4f} r2={1 - (r**2).sum() / ((y - y.mean())**2).sum():.5f}')
