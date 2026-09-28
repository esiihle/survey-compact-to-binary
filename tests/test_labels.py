"""Tests for value-labelled indicator columns (v0.2.0)."""

from __future__ import annotations

import pandas as pd

from compact2binary import convert
from compact2binary.codeframe import Codeframe, Question
from compact2binary.util import format_indicator, slugify


def test_slugify_basics():
    assert slugify("Brand Alpha") == "brand_alpha"
    assert slugify("None of these!") == "none_of_these"
    assert slugify("Coke/Pepsi") == "coke_pepsi"
    assert slugify("   ") == "x"  # never empty


def test_format_indicator_tokens():
    assert format_indicator("{qid}_{code}", "Q3", 4, "Krunch") == "Q3_4"
    assert format_indicator("{qid}_{label}", "Q3", 4, "Krunch") == "Q3_krunch"
    assert format_indicator("{qid}_{code}_{label}", "Q3", 4, "Krunch") == "Q3_4_krunch"


def test_label_template_produces_readable_columns():
    q = Question(qid="Q3", label="Bought", qtype="multi", storage="delimited",
                 column="Q4", delimiter=";", codes={1: "Crispa", 2: "Muncho"})
    cf = Codeframe(questions=[q], output_template="{qid}_{label}")
    df = pd.DataFrame({"Q4": ["1;2", "1"]})
    out = convert(df, cf)
    assert "Q3_crispa" in out.columns
    assert "Q3_muncho" in out.columns
    assert out["Q3_crispa"].tolist() == [1, 1]
    assert out["Q3_muncho"].tolist() == [1, 0]


def test_default_template_unchanged():
    # Backward compatibility: default template still yields code-based names.
    q = Question(qid="Q3", label="Bought", qtype="multi", storage="delimited",
                 column="Q4", delimiter=";", codes={1: "Crispa"})
    cf = Codeframe(questions=[q])
    out = convert(pd.DataFrame({"Q4": ["1"]}), cf)
    assert "Q3_1" in out.columns
