"""Cause c3: viral panel counts. Try several counting rules against the printed counts."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load

df = load()
pub = {"NIV": {"RSV": 91, "Bo": 4, "Ad": 6, "SC": 4, "Pa": 7, "Me": 5, "RE": 2},
       "HFNC": {"RSV": 90, "Bo": 11, "Ad": 9, "SC": 8, "Pa": 5, "Me": 4, "RE": 2}}
toks = df.VP.fillna("").astype(str).apply(lambda s: [t.strip() for t in s.split(",") if t.strip()])
rules = {
    "any mention (both runs)": lambda t, v: v in t,
    "first-listed virus only": lambda t, v: len(t) > 0 and t[0] == v,
    "single-virus infections only": lambda t, v: t == [v],
    "RSV co-infections count as RSV only": lambda t, v: (v in t) if (v == "RSV" or "RSV" not in t) else False,
}
for name, f in rules.items():
    print("Rule:", name)
    for g in ("NIV", "HFNC"):
        tg = toks[df.Gr == g]
        got = {v: int(tg.apply(lambda t: f(t, v)).sum()) for v in pub[g]}
        miss = {v: f"{got[v]} vs {pub[g][v]}" for v in got if got[v] != pub[g][v]}
        print(f"  {g:5s} {got}  mismatches: {miss if miss else 'none'}")
print()
print("Upper bound: HFNC rows that mention Bo at all =",
      int(toks[df.Gr == "HFNC"].apply(lambda t: "Bo" in t).sum()), "(published 11, so no counting rule can reach it)")
nb = toks[df.Gr == "NIV"]
print("NIV rows with Bo =", int(nb.apply(lambda t: "Bo" in t).sum()),
      "; of these without RSV =", int(nb.apply(lambda t: "Bo" in t and "RSV" not in t).sum()),
      "; reaching 4 while RSV stays at 91 needs dropping Bo from RSV co-infections, which also breaks NIV Ad/Pa.")
print("Printed % equal count/126 (4/126 = 3.2%, 11/126 = 8.7%), so the % cells simply follow the counts.")
