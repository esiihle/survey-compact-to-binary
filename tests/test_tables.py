"""Tests for tabular I/O dispatch (v0.2.0)."""

from __future__ import annotations

import pandas as pd

from compact2binary.tables import read_table, write_table


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "respondent_id": ["R1", "R2"],
        "Q3_1": [1, 0],
        "Q3_2": [0, 1],
    })


def test_csv_round_trip(tmp_path):
    p = tmp_path / "x.csv"
    write_table(_frame(), p)
    back = read_table(p, as_str=True)
    assert list(back.columns) == ["respondent_id", "Q3_1", "Q3_2"]
    assert back["Q3_1"].tolist() == ["1", "0"]  # as_str keeps raw form


def test_tsv_round_trip(tmp_path):
    p = tmp_path / "x.tsv"
    write_table(_frame(), p)
    back = read_table(p)
    assert back.shape == (2, 3)


def test_parquet_round_trip(tmp_path):
    # pyarrow is a dev/parquet extra; skip cleanly if unavailable.
    pytest_importorskip = __import__("pytest").importorskip
    pytest_importorskip("pyarrow")
    p = tmp_path / "x.parquet"
    write_table(_frame(), p)
    back = read_table(p)
    assert back.shape == (2, 3)
    assert back["Q3_2"].tolist() == [0, 1]  # native dtypes preserved
