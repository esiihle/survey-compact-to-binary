"""Validation and QC for the conversion.

The validator is deliberately independent of the converter: it re-reads the
original compact data and checks the produced binary frame against it and
against the codeframe. This catches the failure modes that matter in real
survey processing:

* **Unknown codes** - a code present in the data but absent from the
  codeframe (usually a stale codeframe or an upstream recode bug).
* **Unparseable tokens** - cells that are not integer codes.
* **Round-trip mismatch** - the number of indicators set for a respondent
  must equal the number of distinct known codes they actually selected.
* **Domain violations** - every indicator must be 0, 1, or (deliberately) NaN.

The result is a structured :class:`ValidationReport`; nothing is printed here,
so the same report can drive a CLI, a test assertion, or a log line.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .codeframe import Codeframe, Question
from .convert import parse_selected_codes
from .util import format_indicator


@dataclass
class ValidationReport:
    """Outcome of validating one conversion."""

    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # code -> how many times an out-of-frame code appeared, per question
    unknown_codes: dict[str, dict[int, int]] = field(default_factory=dict)
    stats: dict[str, int] = field(default_factory=dict)

    def _fail(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def summary(self) -> str:
        lines = [f"Validation: {'PASS' if self.ok else 'FAIL'}"]
        for k, v in self.stats.items():
            lines.append(f"  {k}: {v}")
        for w in self.warnings:
            lines.append(f"  [warn] {w}")
        for e in self.errors:
            lines.append(f"  [error] {e}")
        return "\n".join(lines)


def validate(
    original: pd.DataFrame,
    converted: pd.DataFrame,
    codeframe: Codeframe,
) -> ValidationReport:
    """Audit a compact->binary conversion.

    Args:
        original: The compact-format input frame.
        converted: The binary-format output of :func:`compact2binary.convert.convert`.
        codeframe: The survey metadata used for the conversion.

    Returns:
        A :class:`ValidationReport`. ``report.ok`` is False if any hard error
        was found.
    """
    report = ValidationReport()
    template = codeframe.output_template

    report.stats["respondents"] = len(original)
    report.stats["multi_questions"] = len(codeframe.multi_questions)
    report.stats["indicator_columns"] = 0

    for q in codeframe.multi_questions:
        _validate_question(original, converted, q, template, report)

    if not report.errors:
        report.stats.setdefault("indicator_columns", 0)
    return report


def _validate_question(
    original: pd.DataFrame,
    converted: pd.DataFrame,
    q: Question,
    template: str,
    report: ValidationReport,
) -> None:
    out_cols = {code: format_indicator(template, q.qid, code, q.codes[code])
                for code in q.codes}
    known = set(q.codes)

    # All expected indicator columns must exist.
    missing_cols = [c for c in out_cols.values() if c not in converted.columns]
    if missing_cols:
        report._fail(f"{q.qid}: missing output columns {missing_cols}")
        return
    report.stats["indicator_columns"] += len(out_cols)

    # Domain check: values must be in {0, 1} (NaN allowed only under nan policy).
    for name in out_cols.values():
        col = converted[name]
        non_null = col.dropna()
        bad = set(non_null.unique()) - {0, 1}
        if bad:
            report._fail(f"{name}: contains non-binary values {sorted(bad)}")
        if col.isna().any() and q.missing_policy != "nan":
            report._fail(f"{name}: unexpected NaN under missing_policy='zero'")

    # Row-level audit: re-parse compact answers and compare to indicators.
    unknown_counter: dict[int, int] = {}
    unparseable_total = 0
    mismatch_rows = 0
    exclusive_violations = 0
    exclusive_set = set(q.exclusive)

    indicator_frame = converted[list(out_cols.values())]
    for pos, (_, row) in enumerate(original.iterrows()):
        codes, unparseable, was_blank = parse_selected_codes(row, q)
        unparseable_total += len(unparseable)

        for c in codes:
            if c not in known:
                unknown_counter[c] = unknown_counter.get(c, 0) + 1

        known_selected = {c for c in codes if c in known}

        # Exclusive-code integrity: an exclusive code (e.g. "None of these")
        # must not appear alongside any other selected code.
        if exclusive_set:
            picked_excl = known_selected & exclusive_set
            if picked_excl and len(known_selected) > 1:
                exclusive_violations += 1

        ind_row = indicator_frame.iloc[pos]
        if ind_row.isna().any():
            # Off-base respondent under nan policy; skip the count check.
            continue
        set_count = int(ind_row.sum())
        if set_count != len(known_selected):
            mismatch_rows += 1

    if unknown_counter:
        report.unknown_codes[q.qid] = dict(sorted(unknown_counter.items()))
        total = sum(unknown_counter.values())
        report._fail(
            f"{q.qid}: {total} occurrence(s) of codes not in codeframe: "
            f"{sorted(unknown_counter)}"
        )
    if unparseable_total:
        report.warnings.append(
            f"{q.qid}: {unparseable_total} unparseable token(s) ignored"
        )
    if mismatch_rows:
        report._fail(
            f"{q.qid}: {mismatch_rows} row(s) where indicator count != "
            f"distinct known codes selected"
        )
    if exclusive_violations:
        excl_labels = ", ".join(q.codes[c] for c in q.exclusive)
        report._fail(
            f"{q.qid}: {exclusive_violations} row(s) select an exclusive code "
            f"({excl_labels}) alongside other codes"
        )
