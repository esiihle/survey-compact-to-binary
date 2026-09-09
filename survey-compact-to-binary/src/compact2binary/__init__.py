"""compact2binary — convert compact multi-response survey data to a 0/1 matrix.

Public API::

    from compact2binary import load_codeframe, convert, validate

    codeframe = load_codeframe("config/codeframe.example.yaml")
    binary = convert(compact_df, codeframe)
    report = validate(compact_df, binary, codeframe)
"""

from __future__ import annotations

from .codeframe import Codeframe, CodeframeError, Question, load_codeframe
from .convert import convert, indicator_columns, parse_selected_codes
from .validate import ValidationReport, validate

__version__ = "0.1.0"

__all__ = [
    "Codeframe",
    "CodeframeError",
    "Question",
    "load_codeframe",
    "convert",
    "indicator_columns",
    "parse_selected_codes",
    "ValidationReport",
    "validate",
    "__version__",
]
