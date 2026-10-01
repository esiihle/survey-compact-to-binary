"""Inverse transform: binary matrix -> compact format.

The converter expands compact storage into a 0/1 matrix; ``decode`` goes the
other way, collapsing each multi-response question's indicator columns back
into a single delimited column of selected codes. This is useful for feeding
other tools that expect compact input, and it makes the pipeline round-trippable
(``decode(convert(x))`` recovers the selected codes).

Notes:

* Output is always *delimited* compact (one column per question), even if the
  original used multi-column storage — a single canonical compact form.
* Net columns and indicator columns are consumed; all other columns pass
  through untouched.
* A respondent with no selected codes (or off-base NaN indicators) yields an
  empty cell — compact storage cannot distinguish "selected none" from
  "not asked", by nature.
"""

from __future__ import annotations

import pandas as pd

from .codeframe import Codeframe
from .nets import net_name
from .util import format_indicator


def _produced_columns(codeframe: Codeframe) -> set[str]:
    """Every column the converter would generate (indicators + nets)."""
    template = codeframe.output_template
    produced: set[str] = set()
    for q in codeframe.multi_questions:
        for code in q.codes:
            produced.add(format_indicator(template, q.qid, code, q.codes[code]))
        for net in q.nets:
            produced.add(net_name(q.qid, net.label))
    return produced


def decode(binary: pd.DataFrame, codeframe: Codeframe) -> pd.DataFrame:
    """Reconstruct compact (delimited) storage from a binary matrix.

    Args:
        binary: A binary indicator matrix (e.g. the converter's output).
        codeframe: The survey metadata that produced it.

    Returns:
        A compact DataFrame: passthrough columns first (in original order),
        then one delimited column per multi-response question.
    """
    template = codeframe.output_template
    produced = _produced_columns(codeframe)

    out = pd.DataFrame(index=binary.index)
    # Passthrough columns (ids, weights, singles) keep their original order.
    for col in binary.columns:
        if col not in produced:
            out[col] = binary[col].values

    for q in codeframe.multi_questions:
        target = q.column or q.qid
        code_cols = [
            (code, format_indicator(template, q.qid, code, q.codes[code]))
            for code in q.codes
        ]
        present = [(code, col) for code, col in code_cols if col in binary.columns]

        values: list[str] = []
        for _, row in binary.iterrows():
            selected = [code for code, col in present
                        if pd.notna(row[col]) and int(row[col]) == 1]
            values.append(q.delimiter.join(str(c) for c in sorted(selected)))
        out[target] = values

    return out
