"""Command-line interface.

Examples::

    # Convert compact -> binary
    python -m compact2binary convert \
        --input data/synthetic_compact.csv \
        --codeframe config/codeframe.example.yaml \
        --output data/synthetic_binary.csv

    # Convert and QC in one step (non-zero exit on failure, for CI)
    python -m compact2binary convert \
        -i data/synthetic_compact.csv \
        -c config/codeframe.example.yaml \
        -o data/synthetic_binary.csv --validate
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from .codeframe import load_codeframe
from .convert import convert
from .validate import validate


def _read_csv(path: str) -> pd.DataFrame:
    # dtype=str keeps codes as written (e.g. leading zeros) and avoids pandas
    # guessing float for integer code columns; the converter parses codes itself.
    return pd.read_csv(path, dtype=str, keep_default_na=True)


def _cmd_convert(args: argparse.Namespace) -> int:
    codeframe = load_codeframe(args.codeframe)
    df = _read_csv(args.input)
    binary = convert(df, codeframe, keep_source=args.keep_source)
    binary.to_csv(args.output, index=False)
    print(f"Wrote {len(binary)} rows x {binary.shape[1]} cols -> {args.output}")

    if args.validate:
        report = validate(df, binary, codeframe)
        print(report.summary())
        return 0 if report.ok else 1
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    codeframe = load_codeframe(args.codeframe)
    original = _read_csv(args.input)
    converted = _read_csv(args.converted)
    report = validate(original, converted, codeframe)
    print(report.summary())
    return 0 if report.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compact2binary",
        description="Convert compact multi-response survey data to a 0/1 matrix.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_conv = sub.add_parser("convert", help="convert compact CSV to binary CSV")
    p_conv.add_argument("-i", "--input", required=True, help="compact CSV path")
    p_conv.add_argument("-c", "--codeframe", required=True, help="codeframe YAML path")
    p_conv.add_argument("-o", "--output", required=True, help="output CSV path")
    p_conv.add_argument(
        "--keep-source", action="store_true",
        help="keep original compact columns alongside the indicators",
    )
    p_conv.add_argument(
        "--validate", action="store_true",
        help="run QC after converting; non-zero exit if it fails",
    )
    p_conv.set_defaults(func=_cmd_convert)

    p_val = sub.add_parser("validate", help="QC an existing conversion")
    p_val.add_argument("-i", "--input", required=True, help="compact CSV path")
    p_val.add_argument("-C", "--converted", required=True, help="binary CSV path")
    p_val.add_argument("-c", "--codeframe", required=True, help="codeframe YAML path")
    p_val.set_defaults(func=_cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
