"""Tabular I/O that dispatches on file extension.

Survey data arrives and leaves in more than one format. This wraps the read
and write so the rest of the pipeline doesn't care which it is:

* ``.csv`` / ``.tsv`` - text; read as strings by default so answer codes keep
  their exact written form (leading zeros, no float coercion).
* ``.parquet`` / ``.pq`` - columnar; requires ``pyarrow`` (``pip install
  '.[parquet]'``). Native dtypes are preserved; the converter parses codes
  from ints/floats just as happily as from strings.
* ``.xlsx`` / ``.xlsm`` - Excel; requires ``openpyxl`` (``pip install
  '.[excel]'``). The first worksheet is read. Handy because survey teams so
  often live in Excel.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_PARQUET_SUFFIXES = {".parquet", ".pq"}
_EXCEL_SUFFIXES = {".xlsx", ".xlsm"}


def _suffix(path: str | Path) -> str:
    return Path(path).suffix.lower()


def read_table(path: str | Path, *, as_str: bool = False) -> pd.DataFrame:
    """Read a table, choosing the reader from the file extension.

    Args:
        path: Input file (.csv, .tsv, .parquet, .pq, .xlsx, .xlsm).
        as_str: For text and Excel formats, read every column as string
            (recommended for raw survey codes). Ignored for Parquet, which
            carries its own types.
    """
    suffix = _suffix(path)
    if suffix in _PARQUET_SUFFIXES:
        try:
            return pd.read_parquet(path)
        except ImportError as exc:  # pragma: no cover - depends on env
            raise ImportError(
                "reading Parquet needs pyarrow: pip install '.[parquet]'"
            ) from exc
    if suffix in _EXCEL_SUFFIXES:
        try:
            dtype = str if as_str else None
            return pd.read_excel(path, dtype=dtype, engine="openpyxl")
        except ImportError as exc:  # pragma: no cover - depends on env
            raise ImportError(
                "reading Excel needs openpyxl: pip install '.[excel]'"
            ) from exc
    sep = "\t" if suffix == ".tsv" else ","
    if as_str:
        return pd.read_csv(path, dtype=str, sep=sep, keep_default_na=True)
    return pd.read_csv(path, sep=sep)


def write_table(df: pd.DataFrame, path: str | Path) -> None:
    """Write a table, choosing the writer from the file extension."""
    suffix = _suffix(path)
    if suffix in _PARQUET_SUFFIXES:
        try:
            df.to_parquet(path, index=False)
        except ImportError as exc:  # pragma: no cover - depends on env
            raise ImportError(
                "writing Parquet needs pyarrow: pip install '.[parquet]'"
            ) from exc
        return
    if suffix in _EXCEL_SUFFIXES:
        try:
            df.to_excel(path, index=False, engine="openpyxl")
        except ImportError as exc:  # pragma: no cover - depends on env
            raise ImportError(
                "writing Excel needs openpyxl: pip install '.[excel]'"
            ) from exc
        return
    sep = "\t" if suffix == ".tsv" else ","
    df.to_csv(path, index=False, sep=sep)
