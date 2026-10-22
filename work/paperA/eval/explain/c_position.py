"""Cause: the authors' mixed models also adjust for the block position of each technique
(1st, 2nd or 3rd technique done, from the 'sequence' column). The Methods name only technique and run.
Compares every model cell with and without that term (all else at the authors' evident choices:
zero knot strength set to 0.1 mm, zero spread kept, Laplace GLMM, Wald z)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.filterwarnings("ignore")
from common import *
pub = published(); rv, rg = runs()
no = table(pos=False)
yes = table(pos=True)
model_cells = [c for c in pub if c.split("|")[1] in ("eff", "lo", "hi", "p")]
print(f"{'cell':11s} {'published':>9s} {'opus':>9s} {'sonnet':>9s} {'no pos':>9s} {'with pos':>9s}  grades(no -> with)")
for c in model_cells:
    g0 = grade(c, rnd(c, no[c], pub), pub)[0]; g1 = grade(c, rnd(c, yes[c], pub), pub)[0]
    print(f"{c:11s} {pub[c]['raw']:>9s} {rv[c]['r_opus']:9.4f} {rv[c]['r_sonnet']:9.4f} {no[c]:9.4f} {yes[c]:9.4f}  {g0} -> {g1}"
          f"   runs: {rg[c]['r_opus']}/{rg[c]['r_sonnet']}")
for lab, t in (("no position term", no), ("with position term", yes)):
    print(lab, "grade counts over 48 model cells:", {g: sum(grade(c, rnd(c, t[c], pub), pub)[0] == g for c in model_cells) for g in "ABCDE"})
# The GLMM integration choice, for the record
print("\nMistakes GLMM, with position term: Laplace (glmer default) vs 15-node adaptive quadrature")
d = add_position(load())
for q in (1, 15):
    r = glmm_contrasts(d, "mb", ("pos",), nagq=q); print(f"  nAGQ={q:2d}", fmt(r, np.exp))
r = glmm_contrasts(d, "mb", (), nagq=15); print("  nAGQ=15 without position (the Sonnet run's model)", fmt(r, np.exp))
