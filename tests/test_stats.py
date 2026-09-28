"""Tests for penetration/frequency statistics (v0.2.0)."""

from __future__ import annotations

import pandas as pd

from compact2binary.codeframe import Codeframe, Question
from compact2binary.stats import penetration


def _codeframe() -> Codeframe:
    q = Question(qid="Q3", label="Bought", qtype="multi", storage="delimited",
                 column="Q3", delimiter=";", codes={1: "Alpha", 2: "Bravo"})
    return Codeframe(questions=[q])


def _binary() -> pd.DataFrame:
    # 4 respondents; Alpha selected by 3, Bravo by 1.
    return pd.DataFrame({
        "respondent_id": ["R1", "R2", "R3", "R4"],
        "weight": [1.0, 1.0, 1.0, 3.0],
        "Q3_1": [1, 1, 1, 0],
        "Q3_2": [0, 0, 0, 1],
    })


def test_unweighted_penetration():
    table = penetration(_binary(), _codeframe())
    alpha = table[table["code"] == 1].iloc[0]
    assert alpha["n"] == 3
    assert alpha["base_n"] == 4
    assert alpha["pct"] == 75.0


def test_weighted_penetration_uses_weights():
    table = penetration(_binary(), _codeframe(), weight_col="weight")
    bravo = table[table["code"] == 2].iloc[0]
    # Bravo only R4 (weight 3) out of total weight 6 -> 50%.
    assert bravo["weighted_n"] == 3.0
    assert bravo["weighted_pct"] == 50.0


def test_penetration_covers_every_code():
    table = penetration(_binary(), _codeframe())
    assert set(table["label"]) == {"Alpha", "Bravo"}


def test_base_excludes_offbase_nan():
    # Under nan missing policy, off-base respondents are NaN and out of base.
    q = Question(qid="Q3", label="x", qtype="multi", storage="delimited",
                 column="Q3", delimiter=";", codes={1: "Alpha"},
                 missing_policy="nan")
    cf = Codeframe(questions=[q])
    binary = pd.DataFrame({"Q3_1": [1, 0, None]})  # third respondent off-base
    table = penetration(binary, cf)
    row = table.iloc[0]
    assert row["base_n"] == 2       # NaN excluded
    assert row["n"] == 1
    assert row["pct"] == 50.0
