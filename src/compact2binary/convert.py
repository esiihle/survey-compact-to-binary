"""Compact -> binary conversion.

The single job of this module: expand every multi-response question from its
*compact* storage (a handful of code-bearing columns) into a *binary* matrix
with one 0/1 indicator column per answer code. Single-response and other
columns are carried through untouched.

Parsing is intentionally forgiving about surface formatting (floats like
``"3.0"``, stray whitespace, empty cells) but never invents data: a token
that cannot be read as an integer code is dropped from the conversion and
surfaced separately by :mod:`compact2binary.validate`, so nothing fails
silently.
"""

from __future__ import annotations

import math
from typing import Iterable

import pandas as pd

from .codeframe import (
    MISSING_NAN,
    MULTI_COLUMN,
    Codeframe,
    Question,
)
from .util import format_indicator


def _clean_token(value: object) -> str | None:
    """Normalise a single cell to a trimmed string, or None if it is blank."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "na", "none", "null"}:
        return None
    return text


def _to_code(token: str) -> int | None:
    """Parse a cleaned token to an integer code, or None if unparseable.

    Accepts plain ints ("3") and integer-valued floats ("3.0"); rejects
    anything genuinely non-integer ("3.5", "other").
    """
    try:
        as_float = float(token)
    except ValueError:
        return None
    if not as_float.is_integer():
        return None
    return int(as_float)


def parse_selected_codes(
    row: "pd.Series", question: Question
) -> tuple[list[int], list[str], bool]:
    """Extract the codes a respondent selected for one multi question.

    Returns a triple ``(codes, unparseable, was_blank)`` where:

    * ``codes`` is the de-duplicated list of integer codes found (order preserved),
    * ``unparseable`` lists raw tokens that could not be read as integers,
    * ``was_blank`` is True when the respondent supplied no tokens at all
      (used to apply the question's missing-data policy).

    Codes are *not* checked against the codeframe here; that audit belongs to
    the validator. This function only reads what is on the row.
    """
    if question.storage == MULTI_COLUMN:
        raw_tokens = [_clean_token(row.get(col)) for col in question.columns]
    else:  # delimited
        cell = _clean_token(row.get(question.column))
        raw_tokens = (
            [t.strip() for t in cell.split(question.delimiter)] if cell else []
        )
        raw_tokens = [t if t != "" else None for t in raw_tokens]

    tokens = [t for t in raw_tokens if t is not None]
    was_blank = len(tokens) == 0

    codes: list[int] = []
    unparseable: list[str] = []
    seen: set[int] = set()
    for tok in tokens:
        code = _to_code(tok)
        if code is None:
            unparseable.append(tok)
            continue
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return codes, unparseable, was_blank


def _expand_multi(df: pd.DataFrame, question: Question, template: str) -> pd.DataFrame:
    """Build the 0/1 indicator frame for one multi question."""
    out_cols = {code: format_indicator(template, question.qid, code,
                                       question.codes[code])
                for code in question.codes}

    # Pre-allocate as object so we can place NaN for off-base respondents.
    data: dict[str, list] = {name: [] for name in out_cols.values()}

    for _, row in df.iterrows():
        codes, _unparseable, was_blank = parse_selected_codes(row, question)
        blank_to_nan = was_blank and question.missing_policy == MISSING_NAN
        selected = set(codes)
        for code, name in out_cols.items():
            if blank_to_nan:
                data[name].append(float("nan"))
            else:
                data[name].append(1 if code in selected else 0)

    result = pd.DataFrame(data, index=df.index)
    # Columns are pure 0/1 -> use a compact integer type; keep nullable Int8
    # so the NaN (off-base) case is representable without upcasting to float.
    for name in out_cols.values():
        result[name] = result[name].astype("Int8")
    return result


def convert(
    df: pd.DataFrame,
    codeframe: Codeframe,
    *,
    keep_source: bool = False,
) -> pd.DataFrame:
    """Convert a compact-format survey frame to binary format.

    Args:
        df: Respondent-level data in compact format.
        codeframe: Survey metadata describing each question.
        keep_source: If True, keep the original compact columns alongside the
            generated indicators. Defaults to False (source columns dropped).

    Returns:
        A new DataFrame with multi-response questions expanded to 0/1
        indicator columns and all other columns preserved in their original
        left-to-right order.
    """
    template = codeframe.output_template
    multi = codeframe.multi_questions
    source_cols: set[str] = set()
    for q in multi:
        source_cols.update(q.source_columns)

    # Start from the passthrough columns, preserving original order.
    if keep_source:
        base = df.copy()
    else:
        keep = [c for c in df.columns if c not in source_cols]
        base = df[keep].copy()

    # Append each question's indicator block, inserting it where the source
    # question sat so related columns stay together in the output.
    pieces: list[pd.DataFrame] = [base]
    for q in multi:
        pieces.append(_expand_multi(df, q, template))

    converted = pd.concat(pieces, axis=1)
    return converted


def indicator_columns(codeframe: Codeframe) -> list[str]:
    """All indicator column names the codeframe will generate, in order."""
    cols: list[str] = []
    for q in codeframe.multi_questions:
        cols.extend(q.output_columns(codeframe.output_template))
    return cols
