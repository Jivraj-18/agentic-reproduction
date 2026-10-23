"""Step 5: for groups still off under the 4p fit, compare each experiment's 4p fit with the authors' row."""
import sys, os, pickle; sys.path.insert(0, os.path.dirname(__file__)); sys.stdout.reconfigure(encoding="utf-8")
from common import *
D = parse()
fits = pickle.load(open(os.path.join(os.path.dirname(__file__), "fits.pkl"), "rb"))
for key in [("cse_3","ach"),("cse_3","dea"),("cse_200","ach"),("eve_ctrl","ach"),("eve_2","ach"),("eve_20","ach"),
            ("eve_undil","dea"),("hte_ctrl","ach"),("hte_undil","dea"),("hte_2","dea"),("hte_20","dea")]:
    d = D[key]; print(f"\n{key}:")
    for e in range(5):
        a = fits[("4p free baseline",) + key][e]; b = fits[("3p free nH (baseline 0)",) + key][e]
        flag = "  <-- differs" if abs(a[0]-(100-d['emax_t'][e]))>1 or abs(np.log10(a[1]/d['ec50'][e]))>0.03 else ""
        print(f"  exp{e+1}: authors Emax {100-d['emax_t'][e]:6.1f} EC50 {d['ec50'][e]*1e9:7.0f} | 4p Emax {a[0]:6.1f} EC50 {a[1]*1e9:7.0f} nH {a[2]:.2f}"
              f" | 3p Emax {b[0]:6.1f} EC50 {b[1]*1e9:7.0f} | relax 0.03-10uM " + "/".join(f"{100-x:.0f}" for x in d['tension'][e][3:]) + flag)
