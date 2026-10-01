"""Tests for net/combination variables (v0.3.0)."""

from __future__ import annotations

import pandas as pd
import pytest

from compact2binary import convert, load_codeframe
from compact2binary.codeframe import Codeframe, CodeframeError, Net, Question
from compact2binary.nets import compute_nets, net_columns, net_name


def _codeframe_with_nets() -> Codeframe:
    q = Question(
        qid="Q3", label="Bought", qtype="multi", storage="delimited",
        column="Q3", delimiter=";",
        codes={1: "Alpha", 2: "Bravo", 3: "Crispa", 9: "None"},
        nets=[Net(label="Any AB", codes=[1, 2])],
    )
    return Codeframe(questions=[q])


def test_net_name_slug():
    assert net_name("Q3", "Any premium") == "Q3_net_any_premium"


def test_net_column_is_or_of_members():
    cf = _codeframe_with_nets()
    df = pd.DataFrame({"Q3": ["1", "2;3", "3", "9"]})
    out = convert(df, cf)
    assert "Q3_net_any_ab" in out.columns
    # R1 has 1 -> 1; R2 has 2 -> 1; R3 has only 3 -> 0; R4 None -> 0
    assert out["Q3_net_any_ab"].tolist() == [1, 1, 0, 0]


def test_net_columns_listed():
    assert net_columns(_codeframe_with_nets()) == ["Q3_net_any_ab"]


def test_net_nan_when_offbase():
    q = Question(qid="Q3", label="x", qtype="multi", storage="delimited",
                 column="Q3", delimiter=";", codes={1: "A", 2: "B"},
                 missing_policy="nan", nets=[Net(label="AB", codes=[1, 2])])
    cf = Codeframe(questions=[q])
    df = pd.DataFrame({"Q3": ["1", ""]})  # second respondent off-base
    out = convert(df, cf)
    assert out["Q3_net_ab"].tolist()[0] == 1
    assert pd.isna(out["Q3_net_ab"].tolist()[1])


def test_loader_reads_nets(tmp_path):
    text = """
questions:
  - id: Q3
    type: multi
    storage: delimited
    column: Q3
    nets:
      - {label: Any AB, codes: [1, 2]}
    codes: {1: A, 2: B, 3: C}
"""
    p = tmp_path / "cf.yaml"
    p.write_text(text)
    cf = load_codeframe(p)
    assert cf.by_id("Q3").nets[0].codes == [1, 2]


def test_loader_rejects_net_code_not_in_codes(tmp_path):
    text = """
questions:
  - id: Q3
    type: multi
    storage: delimited
    column: Q3
    nets:
      - {label: bad, codes: [99]}
    codes: {1: A}
"""
    p = tmp_path / "cf.yaml"
    p.write_text(text)
    with pytest.raises(CodeframeError):
        load_codeframe(p)
