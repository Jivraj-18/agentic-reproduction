"""Writes eval/story.json and checks every non-A cell is covered exactly once per run."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(HERE)

both = lambda cells: {"r_opus": list(cells), "r_sonnet": list(cells)}

story = {
    "short": "High-flow oxygen versus NIV in infants",
    "what": ("Table 1 compares the starting characteristics and some hospital outcomes of 252 babies with bronchiolitis, "
             "half given high-flow nasal oxygen (HFNC) and half given mask ventilation (NIV): counts and percentages, "
             "averages, medians and the p-values that test for a group difference."),
    "verdict": ("Mostly yes: about three in four cells (75 of 101 for Opus, 74 for Sonnet) came out within 2%, but the "
                "virus counts, the antibiotic p-value and a few small figures cannot be rebuilt from the Methods and the shared data."),
    "verdict_note": ("Three p-values miss only because the paper does not say which version of the chi-square test it used, "
                     "and four cells miss because the authors cut digits off instead of rounding. The bigger gaps (virus counts, "
                     "antibiotic p-value) are places where the printed table does not match the authors' own deposited data."),
    "implication": ("A Methods line such as 'chi-square tests were run without Yates' continuity correction' would have fixed three "
                    "p-values at once; the journal should also ask the authors to correct the antibiotic p-value and to reconcile "
                    "the virus counts with the deposited spreadsheet."),
    "model_note": ("The two runs made the same choices in 98 of 101 cells. The one real difference: Opus read a duration typed as "
                   "'17h' as 17 hours and got the published p of 0.0003, while Sonnet dropped it and got 0.0004; with one run per "
                   "model this may be chance rather than a model trait."),
    "headline_cause": "c1",
    "causes": [
        {
            "id": "c1",
            "title": "Which chi-square test: with or without Yates' correction",
            "category": "Original: underspecified",
            "cells": both(["female|p", "pw|p", "prh|p"]),
            "left_unsaid": ("The paper says 'the chi-square test was used' but not whether Yates' continuity correction (a small "
                            "adjustment for 2x2 tables, switched on by default in R) was applied."),
            "ai_did": {"r_opus": "Used the R default, chi-square with Yates' correction.",
                       "r_sonnet": "Used the R default, chi-square with Yates' correction."},
            "authors_did": "Used the plain chi-square test without Yates' correction.",
            "fix": "Add: 'Chi-square tests were computed without Yates' continuity correction.'",
            "evidence": ("Without the correction the p-values are 0.151, 0.327 and 0.213, which print as the published 0.15, 0.3 "
                         "and 0.2; with it they are 0.192, 0.401 and 0.276."),
            "example": {"cell": "female|p", "published": "0.15", "ai": {"r_opus": "0.192", "r_sonnet": "0.192"},
                        "alternative": "0.151"},
            "script": "eval/explain/c1_chisq_yates.py",
        },
        {
            "id": "c2",
            "title": "Antibiotic p-value cannot be right",
            "category": "Original: inconsistent",
            "cells": both(["atb|p"]),
            "left_unsaid": ("The table and the text both print 62 (49%) versus 49 (38%) with p<0.001, but a difference that size "
                            "in groups of 126 is not statistically strong under any standard test."),
            "ai_did": {"r_opus": "Chi-square with Yates' correction on patients with a recorded value: p = 0.156.",
                       "r_sonnet": "Chi-square with Yates' correction, counting missing values as 'no': p = 0.128."},
            "authors_did": "Unknown; the p<0.001 matches the Sedation row just above and may have been copied from it.",
            "fix": "Correct the printed p-value for antibiotic use (about 0.10 to 0.16 depending on the test).",
            "evidence": ("Plain chi-square, Yates, Fisher's exact and one-sided Fisher on either denominator give p between "
                         "0.064 and 0.156; none comes near <0.001."),
            "example": {"cell": "atb|p", "published": "<0.001", "ai": {"r_opus": "0.156", "r_sonnet": "0.128"},
                        "alternative": "0.122 (plain chi-square, best case 0.064 one-sided)"},
            "script": "eval/explain/c2_antibiotic_p.py",
        },
        {
            "id": "c3",
            "title": "Virus counts do not match the shared spreadsheet",
            "category": "Original: inconsistent",
            "cells": both(["v_bo|niv_n", "v_bo|niv_pct", "v_bo|hfnc_n", "v_bo|hfnc_pct", "v_ad|niv_n", "v_ad|niv_pct",
                           "v_sc|niv_n", "v_sc|niv_pct", "v_pa|niv_n", "v_pa|niv_pct", "v_me|niv_n", "v_me|niv_pct"]),
            "left_unsaid": ("The paper does not say how babies with two or three viruses were counted, but more importantly the "
                            "printed counts cannot be produced from the deposited virus results by any counting rule."),
            "ai_did": {"r_opus": "Counted a baby for every virus named in its result, so mixed infections count for each virus.",
                       "r_sonnet": "Same as Opus: every virus named counts."},
            "authors_did": ("Unknown. The high-flow group matches the 'every virus named' rule except bocavirus (11 printed, 10 in "
                            "the data); the NIV group has 12 fewer non-RSV mentions printed than the data hold."),
            "fix": "The authors should check the virus rows against the deposited data and state how mixed infections were counted.",
            "evidence": ("'Every virus named' reproduces RSV, rhinovirus and all high-flow rows except bocavirus. Only 10 high-flow "
                         "babies have bocavirus in the data, so 11 is impossible; NIV bocavirus 4 needs dropping bocavirus from "
                         "babies who also had RSV, which then breaks the NIV adenovirus and parainfluenza counts. First-listed-only "
                         "and single-virus-only rules are worse."),
            "example": {"cell": "v_bo|niv_n", "published": "4", "ai": {"r_opus": "10", "r_sonnet": "10"},
                        "alternative": "no rule gives 4 (first-listed gives 3, other rules 0 to 10)"},
            "script": "eval/explain/c3_viral_panel.py",
        },
        {
            "id": "c4",
            "title": "Authors cut digits instead of rounding",
            "category": "Original: underspecified",
            "cells": both(["atb|hfnc_pct", "pim|niv_sd", "pim|p", "imv_d|niv_q1"]),
            "left_unsaid": "The paper does not say that figures were cut short (truncated) rather than rounded.",
            "ai_did": {"r_opus": "Reported exact values, which round up (38.9, 1.75, 0.495, 3.75).",
                       "r_sonnet": "Reported exact values, which round up (38.9, 1.75, 0.495, 3.75)."},
            "authors_did": "Dropped the extra digits: 38.9 became 38, 1.75 became 1.7, 0.495 became 0.49, 3.75 became 3.7.",
            "fix": "Round all figures in the usual way, or state that they are truncated.",
            "evidence": ("Truncating the runs' own exact values gives 38, 1.7, 0.49 and 3.7, exactly the published figures. The "
                         "same habit shows in cells that graded A anyway (25.4 printed as 25.3, 17.5 as 17.4, 42.9 as 42.8), though "
                         "a few virus percentages are rounded normally."),
            "example": {"cell": "pim|niv_sd", "published": "1.7", "ai": {"r_opus": "1.750", "r_sonnet": "1.750"},
                        "alternative": "1.7"},
            "script": "eval/explain/c4_truncation.py",
        },
        {
            "id": "c5",
            "title": "A duration typed as '17h'",
            "category": "Reproducer choice",
            "cells": {"r_opus": [], "r_sonnet": ["dur|p"]},
            "left_unsaid": ("Nothing in the Methods; one NIV duration in the spreadsheet is typed '17h' instead of 17, and the "
                            "data notes say the column is in hours."),
            "ai_did": {"r_opus": "Read '17h' as 17 hours, keeping all 126 NIV babies.",
                       "r_sonnet": "Treated '17h' as unreadable and dropped that baby (125 NIV babies)."},
            "authors_did": "Kept the value as 17 hours, judging by the p-value.",
            "fix": "None needed in the Methods; the deposit should store the value as a plain number.",
            "evidence": "Keeping 17 hours gives p = 0.00031 (published 0.0003); dropping it gives p = 0.00038.",
            "example": {"cell": "dur|p", "published": "0.0003", "ai": {"r_opus": "0.00031", "r_sonnet": "0.00038"},
                        "alternative": "0.00031"},
            "script": "eval/explain/c5_duration_17h.py",
        },
        {
            "id": "c6",
            "title": "Small unexplained gaps in skewed duration rows",
            "category": "Unknown",
            "cells": both(["dur|niv_q3", "ngt_d|p", "imv_d|hfnc_q3"]),
            "left_unsaid": ("The quartile method is not stated, but no quartile method or patient subset tried gives the printed "
                            "values."),
            "ai_did": {"r_opus": "R's default quartiles and the Wilcoxon test with continuity correction, on patients with a value.",
                       "r_sonnet": "Same as Opus."},
            "authors_did": "Unknown.",
            "fix": "Unknown; the authors would need to share their analysis script.",
            "evidence": ("Nine quartile methods give an NIV duration upper quartile of 77 to 81.5, never 78; the high-flow "
                         "ventilation upper quartile is 5 or 5.25 under every method and subset, never 4.5; tube-days p is 0.0113 "
                         "(Wilcoxon) or 0.009 (t-test), never 0.012."),
            "example": {"cell": "dur|niv_q3", "published": "78", "ai": {"r_opus": "80", "r_sonnet": "81"},
                        "alternative": "77 to 81.5, never 78"},
            "script": "eval/explain/c6_unexplained.py",
        },
        {
            "id": "c7",
            "title": "Initial breathing score spread and p-value",
            "category": "Unknown",
            "cells": both(["wdf|niv_sd", "wdf|hfnc_sd", "wdf|p"]),
            "left_unsaid": ("Nothing obvious: 'initial WDF' (a breathing-difficulty score) at 0 hours reproduces the means of "
                            "5.9, but not the spread or the p-value."),
            "ai_did": {"r_opus": "Used the 0-hour score: SD 0.99 and 0.88, Wilcoxon p 0.98.",
                       "r_sonnet": "Same as Opus."},
            "authors_did": "Unknown.",
            "fix": "Unknown; the authors would need to confirm which score values they summarised.",
            "evidence": ("The 0-hour data give SD 0.99 / 0.88 (published 0.9 / 1.1); swapping the groups gives 0.9 / 1.0, still "
                         "not 1.1. Wilcoxon gives p 0.98 and a t-test 0.84, not 0.9; the 2-hour score has the wrong means."),
            "example": {"cell": "wdf|hfnc_sd", "published": "1.1", "ai": {"r_opus": "0.88", "r_sonnet": "0.88"},
                        "alternative": "no reading found"},
            "script": "eval/explain/c6_unexplained.py",
        },
    ],
    "notes": [
        "The antibiotic p<0.001 also appears in the Discussion text, so the error is not a one-off typo in the table.",
        "The Discussion gives tube days as '3 (2-4) versus 4 (2-5)' for HFNC versus NIV, but the table (and the data) show it the other way round.",
        "Most percentages in the table are truncated rather than rounded (25.3, 17.4, 42.8, 38), but a few are rounded normally (3.2, 4).",
        "The deposited data give age, weight and lengths of stay only as ranges, so those rows were not graded.",
        "In the data, one high-flow baby who was never intubated has 2 days of invasive ventilation recorded; both runs kept it, and it does not change the graded cells.",
    ],
}

# coverage check
grades = json.load(open(os.path.join(EVAL, "grades.json"), encoding="utf-8"))
for run in ("r_opus", "r_sonnet"):
    nonA = {k for k, c in grades["cells"].items() if c["graded"] and c["runs"][run].get("grade") != "A"}
    listed = [x for c in story["causes"] for x in c["cells"][run]]
    assert len(listed) == len(set(listed)), run
    assert set(listed) == nonA, (run, nonA ^ set(listed))
    print(run, "non-A cells:", len(nonA), "covered:", len(listed))
with open(os.path.join(EVAL, "story.json"), "w", encoding="utf-8") as fh:
    json.dump(story, fh, indent=1, ensure_ascii=False)
print("wrote story.json")
