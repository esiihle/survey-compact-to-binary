"""Net / combination variables.

A *net* is a named OR-combination of a question's codes, emitted as one extra
0/1 indicator column. Nets are one of the most common survey deliverables:
"Any premium brand", "Top 3 brands", "Any negative sentiment". Defining them in
the codeframe keeps the rule in one place and out of downstream spreadsheets.

A net column is:

* ``1`` if the respondent selected **any** member code,
* ``0`` if they were on-base but selected none of them,
* ``NaN`` if every member is NaN (off-base / not asked) — the net inherits the
  missing-data policy of its underlying indicators.
"""

from __future__ import annotations

import pandas as pd

from .codeframe import Codeframe
from .util import format_indicator, slugify


def net_name(qid: str, label: str) -> str:
    """Output column name for a net, e.g. ('Q3', 'Any premium') -> Q3_net_any_premium."""
    return f"{qid}_net_{slugify(label)}"


def net_columns(codeframe: Codeframe) -> list[str]:
    """All net column names the codeframe will generate, in order."""
    cols: list[str] = []
    for q in codeframe.multi_questions:
        for net in q.nets:
            cols.append(net_name(q.qid, net.label))
    return cols


def compute_nets(binary: pd.DataFrame, codeframe: Codeframe) -> pd.DataFrame:
    """Build the net columns from an already-expanded binary matrix.

    Args:
        binary: The indicator matrix (the converter's output).
        codeframe: Survey metadata carrying each question's net definitions.

    Returns:
        A DataFrame (aligned to ``binary``) with one column per net; empty if
        the codeframe defines no nets.
    """
    template = codeframe.output_template
    out = pd.DataFrame(index=binary.index)
    for q in codeframe.multi_questions:
        for net in q.nets:
            members = [format_indicator(template, q.qid, code, q.codes[code])
                       for code in net.codes]
            present = [m for m in members if m in binary.columns]
            if not present:
                continue
            block = binary[present].apply(pd.to_numeric, errors="coerce")
            # OR across members; max(skipna) is NaN only when every member is NaN.
            out[net_name(q.qid, net.label)] = block.max(axis=1).astype("Int8")
    return out
