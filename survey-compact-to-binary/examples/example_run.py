"""End-to-end example using the Python API (no CLI).

Run from the repo root:

    python examples/example_run.py

It generates a small synthetic dataset in memory-adjacent form, converts it,
validates it, and prints a before/after preview so you can see the shape of
the transformation at a glance.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

from compact2binary import convert, load_codeframe, validate

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    compact_path = ROOT / "examples" / "sample_data" / "sample_compact.csv"
    codeframe_path = ROOT / "config" / "codeframe.example.yaml"

    # Fall back to generating a small dataset if the sample is absent.
    if not compact_path.exists():
        compact_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_synthetic_data.py"),
             "--rows", "15", "--seed", "3", "--out", str(compact_path)],
            check=True,
        )

    codeframe = load_codeframe(codeframe_path)
    compact = pd.read_csv(compact_path, dtype=str)

    print("=== COMPACT (input) ===")
    print(compact.head(5).to_string(index=False))

    binary = convert(compact, codeframe)
    print("\n=== BINARY (output) ===")
    print(binary.head(5).to_string(index=False))

    report = validate(compact, binary, codeframe)
    print("\n=== VALIDATION ===")
    print(report.summary())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
