"""Tests for the compact->binary pipeline.

Run with: pytest -q
"""

from __future__ import annotations

import pandas as pd
import pytest

from compact2binary import convert, load_codeframe, validate
from compact2binary.codeframe import (
    Codeframe,
    CodeframeError,
    Question,
)
from compact2binary.convert import parse_selected_codes


def make_codeframe() -> Codeframe:
    q_single = Question(
        qid="Q1", label="Age", qtype="single", column="Q1",
        codes={1: "young", 2: "old"},
    )
    q_mcol = Question(
        qid="Q3", label="Bought", qtype="multi", storage="multi_column",
        columns=["Q3_m1", "Q3_m2", "Q3_m3"], codes={1: "A", 2: "B", 3: "C"},
    )
    q_delim = Question(
        qid="Q4", label="Aware", qtype="multi", storage="delimited",
        column="Q4", delimiter=";", codes={1: "A", 2: "B", 3: "C"},
    )
    return Codeframe(questions=[q_single, q_mcol, q_delim])


def make_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "respondent_id": ["R1", "R2", "R3"],
            "weight": ["1.0", "0.5", "1.2"],
            "Q1": ["1", "2", "1"],
            "Q3_m1": ["1", "3", ""],       # R3 selected nothing in Q3
            "Q3_m2": ["2", "", ""],
            "Q3_m3": ["", "", ""],
            "Q4": ["1;2;3", "2", ""],
        }
    )


def test_multi_column_expansion():
    cf = make_codeframe()
    out = convert(make_frame(), cf)
    # R1 bought {1,2}, R2 bought {3}, R3 bought {}
    assert out.loc[0, ["Q3_1", "Q3_2", "Q3_3"]].tolist() == [1, 1, 0]
    assert out.loc[1, ["Q3_1", "Q3_2", "Q3_3"]].tolist() == [0, 0, 1]
    assert out.loc[2, ["Q3_1", "Q3_2", "Q3_3"]].tolist() == [0, 0, 0]


def test_delimited_expansion():
    cf = make_codeframe()
    out = convert(make_frame(), cf)
    assert out.loc[0, ["Q4_1", "Q4_2", "Q4_3"]].tolist() == [1, 1, 1]
    assert out.loc[1, ["Q4_1", "Q4_2", "Q4_3"]].tolist() == [0, 1, 0]
    assert out.loc[2, ["Q4_1", "Q4_2", "Q4_3"]].tolist() == [0, 0, 0]


def test_passthrough_columns_preserved():
    cf = make_codeframe()
    out = convert(make_frame(), cf)
    # ID, weight and the single-response Q1 survive untouched.
    assert out["respondent_id"].tolist() == ["R1", "R2", "R3"]
    assert out["weight"].tolist() == ["1.0", "0.5", "1.2"]
    assert out["Q1"].tolist() == ["1", "2", "1"]


def test_source_columns_dropped_by_default():
    cf = make_codeframe()
    out = convert(make_frame(), cf)
    for col in ["Q3_m1", "Q3_m2", "Q3_m3", "Q4"]:
        assert col not in out.columns


def test_keep_source_option():
    cf = make_codeframe()
    out = convert(make_frame(), cf, keep_source=True)
    assert "Q3_m1" in out.columns and "Q4" in out.columns


def test_indicator_columns_are_binary_int8():
    cf = make_codeframe()
    out = convert(make_frame(), cf)
    for col in ["Q3_1", "Q4_1"]:
        assert str(out[col].dtype) == "Int8"
        assert set(out[col].dropna().unique()) <= {0, 1}


def test_duplicate_codes_deduplicated():
    q = Question(
        qid="Q3", label="x", qtype="multi", storage="delimited",
        column="Q4", delimiter=";", codes={1: "A", 2: "B"},
    )
    row = pd.Series({"Q4": "1;1;2;2"})
    codes, unparseable, blank = parse_selected_codes(row, q)
    assert codes == [1, 2]
    assert unparseable == []
    assert blank is False


def test_float_and_whitespace_tokens_parse():
    q = Question(
        qid="Q3", label="x", qtype="multi", storage="delimited",
        column="Q4", delimiter=";", codes={1: "A", 2: "B"},
    )
    row = pd.Series({"Q4": " 1.0 ; 2 "})
    codes, unparseable, blank = parse_selected_codes(row, q)
    assert codes == [1, 2]
    assert unparseable == []


def test_unparseable_token_reported_not_crash():
    q = Question(
        qid="Q3", label="x", qtype="multi", storage="delimited",
        column="Q4", delimiter=";", codes={1: "A"},
    )
    row = pd.Series({"Q4": "1;x;2.5"})
    codes, unparseable, blank = parse_selected_codes(row, q)
    assert codes == [1]
    assert set(unparseable) == {"x", "2.5"}


def test_validate_passes_on_clean_data():
    cf = make_codeframe()
    df = make_frame()
    out = convert(df, cf)
    report = validate(df, out, cf)
    assert report.ok, report.summary()
    assert report.stats["respondents"] == 3


def test_validate_flags_unknown_code():
    cf = make_codeframe()
    df = make_frame()
    df.loc[0, "Q3_m1"] = "99"  # not in codeframe
    out = convert(df, cf)
    report = validate(df, out, cf)
    assert not report.ok
    assert "Q3" in report.unknown_codes
    assert 99 in report.unknown_codes["Q3"]


def test_missing_policy_nan():
    q = Question(
        qid="Q3", label="x", qtype="multi", storage="delimited",
        column="Q4", delimiter=";", codes={1: "A", 2: "B"},
        missing_policy="nan",
    )
    cf = Codeframe(questions=[q])
    df = pd.DataFrame({"Q4": ["1;2", ""]})
    out = convert(df, cf)
    # Row 0 answered -> 0/1; row 1 blank under nan policy -> NaN indicators.
    assert out.loc[0, "Q3_1"] == 1
    assert pd.isna(out.loc[1, "Q3_1"])
    report = validate(df, out, cf)
    assert report.ok, report.summary()


def test_loader_rejects_duplicate_ids(tmp_path):
    text = """
questions:
  - id: Q1
    type: single
    column: Q1
    codes: {1: a}
  - id: Q1
    type: single
    column: Q1b
    codes: {1: a}
"""
    p = tmp_path / "cf.yaml"
    p.write_text(text)
    with pytest.raises(CodeframeError):
        load_codeframe(p)


def test_loader_rejects_bad_type(tmp_path):
    text = """
questions:
  - id: Q1
    type: ranking
    column: Q1
    codes: {1: a}
"""
    p = tmp_path / "cf.yaml"
    p.write_text(text)
    with pytest.raises(CodeframeError):
        load_codeframe(p)
