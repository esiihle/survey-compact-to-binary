"""Tests for the decode (binary -> compact) inverse transform (v0.3.0)."""

from __future__ import annotations

import pandas as pd

from compact2binary import convert
from compact2binary.codeframe import Codeframe, Net, Question
from compact2binary.decode import decode


def _codeframe() -> Codeframe:
    q = Question(qid="Q3", label="Bought", qtype="multi", storage="delimited",
                 column="Q3", delimiter=";", codes={1: "A", 2: "B", 3: "C"})
    return Codeframe(questions=[q])


def test_round_trip_delimited():
    cf = _codeframe()
    compact = pd.DataFrame({
        "respondent_id": ["R1", "R2", "R3"],
        "Q3": ["1;3", "2", ""],
    })
    binary = convert(compact, cf)
    back = decode(binary, cf)
    # Codes come back sorted and joined; blank stays blank.
    assert back["Q3"].tolist() == ["1;3", "2", ""]
    assert back["respondent_id"].tolist() == ["R1", "R2", "R3"]


def test_decode_ignores_net_columns():
    q = Question(qid="Q3", label="x", qtype="multi", storage="delimited",
                 column="Q3", delimiter=";", codes={1: "A", 2: "B"},
                 nets=[Net(label="AB", codes=[1, 2])])
    cf = Codeframe(questions=[q])
    binary = convert(pd.DataFrame({"Q3": ["1;2", "1"]}), cf)
    assert "Q3_net_ab" in binary.columns
    back = decode(binary, cf)
    # Net column is consumed, not treated as passthrough.
    assert "Q3_net_ab" not in back.columns
    assert back["Q3"].tolist() == ["1;2", "1"]


def test_passthrough_columns_preserved():
    cf = _codeframe()
    compact = pd.DataFrame({"respondent_id": ["R1"], "weight": ["1.5"], "Q3": ["2"]})
    back = decode(convert(compact, cf), cf)
    assert back["weight"].tolist() == ["1.5"]
