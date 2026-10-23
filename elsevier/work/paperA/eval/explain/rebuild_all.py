"""Full Table 1 under the authors' evident choices:
 - bracketed means = average of the three per-run arithmetic means (Table 2's bracketed values);
 - every mixed model: technique + run + block position (1st/2nd/3rd technique), random intercept per participant;
 - the single zero delta knot strength set to 0.1 mm before logging; the matching zero spread kept;
 - mistakes: >=1 vs 0, logistic GLMM by Laplace (glmer default); Wald z CIs and p."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.filterwarnings("ignore")
from common import *
pub = published(); rv, rg = runs()
alt = table(pos=True, ks_zero=0.1, sp_zero="keep", nagq=1, means="runmeans")
cnt = {g: 0 for g in "ABCDE"}
for c in pub:
    v = alt[c]; gr, dev = grade(c, rnd(c, v, pub), pub); cnt[gr] += 1
    flag = "" if gr == "A" else "   <-- not A"
    print(f"{c:11s} published={pub[c]['raw']:>7s} rebuilt={v:10.4f} {gr} ({dev:4.1f}%)  runs: opus {rg[c]['r_opus']} / sonnet {rg[c]['r_sonnet']}{flag}")
print("Grade counts, authors' reading:", cnt)
print("Runs for comparison: opus", {g: sum(rg[c]['r_opus'] == g for c in pub) for g in "ABCDE"},
      "sonnet", {g: sum(rg[c]['r_sonnet'] == g for c in pub) for g in "ABCDE"})
print("Notes: mi B mean is exactly 11/40 = 0.275 (prints 0.28 in R; float summation here gives 0.27499...).")
print("       ks_io|p: Wald z gives 0.0420; a t reference with ~437 df (lmerTest-style) gives 0.0426 -> 0.043.")
print("       sp_io|m1 is printed 11.72 but the same mean is printed 11.77 two rows below and in the text; 11.766 rebuilt.")
