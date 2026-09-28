"""Tests for the exclusive-code integrity check (v0.2.0)."""

from __future__ import annotations

import pandas as pd
import pytest

from compact2binary import convert, load_codeframe, validate
from compact2binary.codeframe import Codeframe, CodeframeError, Question


def _codeframe_with_exclusive() -> Codeframe:
    q = Question(
        qid="Q3", label="Bought", qtype="multi", storage="delimited",
        column="Q3", delimiter=";",
        codes={1: "Alpha", 2: "Bravo", 9: "None of these"},
        exclusive=[9],
    )
    return Codeframe(questions=[q])


def test_exclusive_only_answer_is_valid():
    cf = _codeframe_with_exclusive()
    df = pd.DataFrame({"Q3": ["9", "1;2"]})  # None-only, then two brands
    out = convert(df, cf)
    report = validate(df, out, cf)
    assert report.ok, report.summary()


def test_exclusive_cooccurrence_is_flagged():
    cf = _codeframe_with_exclusive()
    df = pd.DataFrame({"Q3": ["9;1", "2"]})  # None + a brand -> violation
    out = convert(df, cf)
    report = validate(df, out, cf)
    assert not report.ok
    assert any("exclusive" in e for e in report.errors)


def test_loader_reads_exclusive(tmp_path):
    text = """
questions:
  - id: Q3
    type: multi
    storage: delimited
    column: Q3
    exclusive: [9]
    codes: {1: Alpha, 9: None of these}
"""
    p = tmp_path / "cf.yaml"
    p.write_text(text)
    cf = load_codeframe(p)
    assert cf.by_id("Q3").exclusive == [9]


def test_loader_rejects_exclusive_not_in_codes(tmp_path):
    text = """
questions:
  - id: Q3
    type: multi
    storage: delimited
    column: Q3
    exclusive: [99]
    codes: {1: Alpha}
"""
    p = tmp_path / "cf.yaml"
    p.write_text(text)
    with pytest.raises(CodeframeError):
        load_codeframe(p)
