"""Tests for Excel (.xlsx) table I/O (v0.3.0)."""

from __future__ import annotations

import pandas as pd
import pytest

from compact2binary.tables import read_table, write_table


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "respondent_id": ["R1", "R2"],
        "Q3_1": [1, 0],
        "Q3_2": [0, 1],
    })


def test_xlsx_round_trip(tmp_path):
    pytest.importorskip("openpyxl")
    p = tmp_path / "x.xlsx"
    write_table(_frame(), p)
    back = read_table(p)
    assert list(back.columns) == ["respondent_id", "Q3_1", "Q3_2"]
    assert back.shape == (2, 3)
    assert back["Q3_2"].tolist() == [0, 1]


def test_xlsx_as_str(tmp_path):
    pytest.importorskip("openpyxl")
    p = tmp_path / "x.xlsx"
    write_table(_frame(), p)
    back = read_table(p, as_str=True)
    assert back["Q3_1"].tolist() == ["1", "0"]
