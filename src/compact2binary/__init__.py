"""compact2binary — convert compact multi-response survey data to a 0/1 matrix.

Public API::

    from compact2binary import load_codeframe, convert, validate

    codeframe = load_codeframe("config/codeframe.example.yaml")
    binary = convert(compact_df, codeframe)
    report = validate(compact_df, binary, codeframe)
"""

from __future__ import annotations

from .codeframe import Codeframe, CodeframeError, Net, Question, load_codeframe
from .convert import convert, indicator_columns, parse_selected_codes
from .decode import decode
from .nets import compute_nets, net_columns, net_name
from .stats import format_penetration, penetration
from .tables import read_table, write_table
from .util import format_indicator, slugify
from .validate import ValidationReport, validate

__version__ = "0.3.0"

__all__ = [
    "Codeframe",
    "CodeframeError",
    "Net",
    "Question",
    "load_codeframe",
    "convert",
    "indicator_columns",
    "parse_selected_codes",
    "ValidationReport",
    "validate",
    "penetration",
    "format_penetration",
    "compute_nets",
    "net_columns",
    "net_name",
    "decode",
    "read_table",
    "write_table",
    "format_indicator",
    "slugify",
    "__version__",
]
