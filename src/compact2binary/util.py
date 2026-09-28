"""Small shared helpers.

Kept separate so both the converter and the validator name indicator columns
through exactly the same function — if the naming rule ever changes, it changes
in one place.
"""

from __future__ import annotations

import re


def slugify(text: str) -> str:
    """Turn an answer label into an ASCII, lower-case, underscore-safe token.

    Examples:
        "Brand Alpha"     -> "brand_alpha"
        "None of these!"  -> "none_of_these"
        "Coke/Pepsi"      -> "coke_pepsi"
    """
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(text).strip().lower())
    return s.strip("_") or "x"


def format_indicator(template: str, qid: str, code: int, label: str) -> str:
    """Build one indicator column name from the codeframe's output template.

    The template may reference any of three placeholders:

    * ``{qid}``   - the question id (e.g. "Q3")
    * ``{code}``  - the integer answer code (e.g. 4)
    * ``{label}`` - the answer label, slugified (e.g. "krunch")

    The default template ``"{qid}_{code}"`` ignores the label, so existing
    codeframes are unaffected. Set e.g. ``"{qid}_{label}"`` for readable
    columns like ``Q3_krunch``, or ``"{qid}_{code}_{label}"`` for both.
    """
    return template.format(qid=qid, code=code, label=slugify(label))
