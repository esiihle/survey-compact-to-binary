"""Codeframe model and loader.

A *codeframe* is the survey metadata that tells the converter how each
variable is stored and what its answer codes mean. It is the single source
of truth for the whole pipeline: nothing about a specific survey is
hard-coded in the conversion logic — it all lives in a codeframe YAML file.

Two question storage layouts are supported for multi-response questions:

* ``multi_column``  - one column per "mention", each cell holding a single
  code (e.g. ``Q3_m1=3``, ``Q3_m2=7``). Blank cells mean "no further
  mentions". This is how Q / SPSS often export multi-response grids.
* ``delimited``     - a single column holding several codes joined by a
  delimiter (e.g. ``"3;7;12"``).

Single-response questions and any other columns (IDs, weights, open-ends)
are passed through untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Storage layouts we know how to parse for multi-response questions.
MULTI_COLUMN = "multi_column"
DELIMITED = "delimited"
_VALID_MULTI_STORAGE = {MULTI_COLUMN, DELIMITED}

# How to treat a respondent whose compact answer is entirely blank.
MISSING_ZERO = "zero"  # answered, selected nothing -> all indicators 0
MISSING_NAN = "nan"    # off-base / not asked -> all indicators NaN
_VALID_MISSING = {MISSING_ZERO, MISSING_NAN}


class CodeframeError(ValueError):
    """Raised when a codeframe file is structurally invalid."""


@dataclass
class Question:
    """One survey question described in the codeframe.

    Attributes:
        qid: Short question id, used as the output-column prefix (e.g. ``Q3``).
        label: Human-readable question text (documentation only).
        qtype: ``"single"`` or ``"multi"``.
        codes: Mapping of integer code -> answer label.
        storage: For multi questions, ``"multi_column"`` or ``"delimited"``.
        columns: For ``multi_column`` storage, the source mention columns.
        column: For ``delimited`` or ``single`` storage, the single source column.
        delimiter: For ``delimited`` storage, the separator between codes.
        missing_policy: How to fill indicators when the compact answer is blank.
    """

    qid: str
    label: str
    qtype: str
    codes: dict[int, str] = field(default_factory=dict)
    storage: str | None = None
    columns: list[str] = field(default_factory=list)
    column: str | None = None
    delimiter: str = ";"
    missing_policy: str = MISSING_ZERO

    @property
    def is_multi(self) -> bool:
        return self.qtype == "multi"

    @property
    def source_columns(self) -> list[str]:
        """All input columns this question reads from."""
        if self.storage == MULTI_COLUMN:
            return list(self.columns)
        if self.column is not None:
            return [self.column]
        return []

    def output_columns(self, template: str) -> list[str]:
        """Names of the binary indicator columns this question produces."""
        return [template.format(qid=self.qid, code=code) for code in self.codes]


@dataclass
class Codeframe:
    """A whole survey's worth of question metadata."""

    questions: list[Question]
    # Template for naming generated indicator columns. ``{qid}`` and ``{code}``
    # are substituted, e.g. "Q3_1", "Q3_2", ...
    output_template: str = "{qid}_{code}"

    @property
    def multi_questions(self) -> list[Question]:
        return [q for q in self.questions if q.is_multi]

    def by_id(self, qid: str) -> Question:
        for q in self.questions:
            if q.qid == qid:
                return q
        raise KeyError(qid)


def _require(mapping: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in mapping:
        raise CodeframeError(f"{ctx}: missing required key '{key}'")
    return mapping[key]


def _parse_codes(raw: Any, ctx: str) -> dict[int, str]:
    if not isinstance(raw, dict):
        raise CodeframeError(f"{ctx}: 'codes' must be a mapping of code -> label")
    codes: dict[int, str] = {}
    for k, v in raw.items():
        try:
            code = int(k)
        except (TypeError, ValueError):
            raise CodeframeError(f"{ctx}: code '{k}' is not an integer")
        codes[code] = str(v)
    if not codes:
        raise CodeframeError(f"{ctx}: 'codes' is empty")
    return codes


def _parse_question(raw: dict[str, Any], index: int) -> Question:
    ctx = f"question[{index}]"
    qid = str(_require(raw, "id", ctx))
    ctx = f"question '{qid}'"
    qtype = str(_require(raw, "type", ctx))
    if qtype not in {"single", "multi"}:
        raise CodeframeError(f"{ctx}: type must be 'single' or 'multi', got '{qtype}'")

    codes = _parse_codes(_require(raw, "codes", ctx), ctx)
    label = str(raw.get("label", qid))
    missing_policy = str(raw.get("missing_policy", MISSING_ZERO))
    if missing_policy not in _VALID_MISSING:
        raise CodeframeError(
            f"{ctx}: missing_policy must be one of {sorted(_VALID_MISSING)}"
        )

    if qtype == "single":
        column = str(_require(raw, "column", ctx))
        return Question(
            qid=qid, label=label, qtype=qtype, codes=codes,
            column=column, missing_policy=missing_policy,
        )

    # multi
    storage = str(_require(raw, "storage", ctx))
    if storage not in _VALID_MULTI_STORAGE:
        raise CodeframeError(
            f"{ctx}: storage must be one of {sorted(_VALID_MULTI_STORAGE)}"
        )
    if storage == MULTI_COLUMN:
        cols = _require(raw, "columns", ctx)
        if not isinstance(cols, list) or not cols:
            raise CodeframeError(f"{ctx}: 'columns' must be a non-empty list")
        return Question(
            qid=qid, label=label, qtype=qtype, codes=codes, storage=storage,
            columns=[str(c) for c in cols], missing_policy=missing_policy,
        )
    # delimited
    column = str(_require(raw, "column", ctx))
    delimiter = str(raw.get("delimiter", ";"))
    return Question(
        qid=qid, label=label, qtype=qtype, codes=codes, storage=storage,
        column=column, delimiter=delimiter, missing_policy=missing_policy,
    )


def load_codeframe(path: str | Path) -> Codeframe:
    """Load and validate a codeframe from a YAML file."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise CodeframeError("top level of codeframe must be a mapping")

    raw_questions = _require(raw, "questions", "codeframe")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise CodeframeError("'questions' must be a non-empty list")

    questions = [_parse_question(q, i) for i, q in enumerate(raw_questions)]

    # Guard against duplicate question ids, which would collide on output.
    seen: set[str] = set()
    for q in questions:
        if q.qid in seen:
            raise CodeframeError(f"duplicate question id '{q.qid}'")
        seen.add(q.qid)

    output_template = str(raw.get("output_template", "{qid}_{code}"))
    return Codeframe(questions=questions, output_template=output_template)
