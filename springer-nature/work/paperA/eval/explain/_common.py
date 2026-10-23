import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
PAPER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def load():
    return pd.read_excel(os.path.join(PAPER, "source", "data", "repository_HFNC_x_NIV.xlsx"))


def num(s, parse_h=True):
    s = s.astype(str).str.strip()
    if parse_h:
        s = s.str.replace(r"h$", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def yn(s):
    return s.astype(str).str.strip().map({"y": 1.0, "n": 0.0})
