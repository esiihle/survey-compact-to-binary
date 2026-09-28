"""Penetration / frequency statistics.

Once data is in binary form, the first thing an analyst usually wants is
*penetration*: for each answer code, what share of respondents selected it.
This module computes that from a binary matrix, weighted when a weight column
is supplied, and returns a tidy table ready to print or export.

Base handling mirrors the converter's missing-data policy: a respondent whose
indicator is NaN (off-base / not asked) is excluded from that question's base,
so percentages are taken over the correct denominator.
"""

from __future__ import annotations

import pandas as pd

from .codeframe import Codeframe
from .util import format_indicator


def penetration(
    binary: pd.DataFrame,
    codeframe: Codeframe,
    weight_col: str | None = None,
) -> pd.DataFrame:
    """Compute per-code penetration for every multi-response question.

    Args:
        binary: A binary indicator matrix (e.g. the converter's output).
        codeframe: The survey metadata used to produce that matrix.
        weight_col: Optional weight column; when given, weighted columns are
            added and percentages are weighted.

    Returns:
        A tidy DataFrame, one row per (question, code), with counts,
        base sizes, and percentages (plus weighted equivalents if weighted).
    """
    template = codeframe.output_template
    weighted = bool(weight_col and weight_col in binary.columns)
    if weighted:
        weights = pd.to_numeric(binary[weight_col], errors="coerce").fillna(0.0)

    rows: list[dict[str, object]] = []
    for q in codeframe.multi_questions:
        for code, label in q.codes.items():
            col = format_indicator(template, q.qid, code, label)
            if col not in binary.columns:
                raise KeyError(
                    f"expected indicator column '{col}' not found in input; "
                    "is this the matrix this codeframe produced?"
                )
            ind = pd.to_numeric(binary[col], errors="coerce")
            asked = ind.notna()               # off-base respondents excluded
            selected = ind == 1

            base_n = int(asked.sum())
            n = int(selected.sum())
            pct = (n / base_n * 100.0) if base_n else 0.0

            row: dict[str, object] = {
                "question": q.qid,
                "code": code,
                "label": label,
                "n": n,
                "base_n": base_n,
                "pct": round(pct, 2),
            }
            if weighted:
                w_base = float(weights[asked].sum())
                w_n = float(weights[selected].sum())
                w_pct = (w_n / w_base * 100.0) if w_base else 0.0
                row["weighted_n"] = round(w_n, 2)
                row["weighted_pct"] = round(w_pct, 2)
            rows.append(row)

    return pd.DataFrame(rows)


def format_penetration(table: pd.DataFrame) -> str:
    """Render a penetration table as readable fixed-width text."""
    if table.empty:
        return "(no multi-response questions to summarise)"
    return table.to_string(index=False)
