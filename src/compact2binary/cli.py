"""Command-line interface.

Subcommands:

* ``convert``  - compact -> binary, optional inline QC (``--validate``)
* ``validate`` - QC an existing conversion against its codeframe
* ``stats``    - per-code penetration/frequency table (weighted if asked)
* ``decode``   - inverse transform: binary matrix back to compact form

Input and output may be CSV, TSV, Parquet, or Excel (.xlsx); the format is
chosen from the file extension. Examples::

    # Convert, with human-readable labelled columns and inline QC
    compact2binary convert -i data/compact.csv -c config/codeframe.example.yaml \
        -o data/binary.parquet --labels --validate

    # Penetration table, weighted, written to CSV
    compact2binary stats -i data/binary.csv -c config/codeframe.example.yaml \
        --weight weight -o data/penetration.csv

    # Round-trip: rebuild compact data from the binary matrix
    compact2binary decode -i data/binary.csv -c config/codeframe.example.yaml \
        -o data/compact_again.csv
"""

from __future__ import annotations

import argparse
import sys

from .codeframe import load_codeframe
from .convert import convert
from .decode import decode
from .logging_setup import configure_logging
from .stats import format_penetration, penetration
from .tables import read_table, write_table
from .validate import validate


def _common_flags(parser: argparse.ArgumentParser) -> None:
    """Flags shared by every subcommand."""
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="verbose (debug-level) logging")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="quiet: warnings and errors only")


def _apply_label_template(codeframe, labels: bool):
    """If --labels was passed, switch to a readable label-based column name."""
    if labels and codeframe.output_template == "{qid}_{code}":
        codeframe.output_template = "{qid}_{label}"
    return codeframe


def _cmd_convert(args: argparse.Namespace, log) -> int:
    codeframe = _apply_label_template(load_codeframe(args.codeframe), args.labels)
    df = read_table(args.input, as_str=True)
    binary = convert(df, codeframe, keep_source=args.keep_source)
    write_table(binary, args.output)
    log.info(f"Wrote {len(binary)} rows x {binary.shape[1]} cols -> {args.output}")

    if args.validate:
        report = validate(df, binary, codeframe)
        log.info(report.summary())
        return 0 if report.ok else 1
    return 0


def _cmd_validate(args: argparse.Namespace, log) -> int:
    codeframe = _apply_label_template(load_codeframe(args.codeframe), args.labels)
    original = read_table(args.input, as_str=True)
    # Read the converted matrix with native types so 0/1 indicators are numeric.
    converted = read_table(args.converted, as_str=False)
    report = validate(original, converted, codeframe)
    log.info(report.summary())
    return 0 if report.ok else 1


def _cmd_stats(args: argparse.Namespace, log) -> int:
    codeframe = _apply_label_template(load_codeframe(args.codeframe), args.labels)
    binary = read_table(args.input, as_str=False)
    table = penetration(binary, codeframe, weight_col=args.weight)
    if args.output:
        write_table(table, args.output)
        log.info(f"Wrote penetration table ({len(table)} rows) -> {args.output}")
    else:
        # The table is the data product here, so it goes to stdout.
        print(format_penetration(table))
    return 0


def _cmd_decode(args: argparse.Namespace, log) -> int:
    codeframe = _apply_label_template(load_codeframe(args.codeframe), args.labels)
    binary = read_table(args.input, as_str=False)
    compact = decode(binary, codeframe)
    write_table(compact, args.output)
    log.info(f"Wrote {len(compact)} rows x {compact.shape[1]} cols -> {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compact2binary",
        description="Convert compact multi-response survey data to a 0/1 matrix.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # convert -----------------------------------------------------------------
    p_conv = sub.add_parser("convert", help="convert compact data to binary")
    _common_flags(p_conv)
    p_conv.add_argument("-i", "--input", required=True,
                        help="compact input (.csv/.tsv/.parquet)")
    p_conv.add_argument("-c", "--codeframe", required=True, help="codeframe YAML")
    p_conv.add_argument("-o", "--output", required=True,
                        help="binary output (.csv/.tsv/.parquet)")
    p_conv.add_argument("--labels", action="store_true",
                        help="name indicators by slugified label (Q3_krunch) "
                             "instead of code (Q3_4)")
    p_conv.add_argument("--keep-source", action="store_true",
                        help="keep original compact columns alongside indicators")
    p_conv.add_argument("--validate", action="store_true",
                        help="run QC after converting; non-zero exit on failure")
    p_conv.set_defaults(func=_cmd_convert)

    # validate ----------------------------------------------------------------
    p_val = sub.add_parser("validate", help="QC an existing conversion")
    _common_flags(p_val)
    p_val.add_argument("-i", "--input", required=True, help="compact input")
    p_val.add_argument("-C", "--converted", required=True, help="binary matrix")
    p_val.add_argument("-c", "--codeframe", required=True, help="codeframe YAML")
    p_val.add_argument("--labels", action="store_true",
                        help="expect label-based indicator names (see convert)")
    p_val.set_defaults(func=_cmd_validate)

    # stats -------------------------------------------------------------------
    p_stat = sub.add_parser("stats", help="per-code penetration/frequency table")
    _common_flags(p_stat)
    p_stat.add_argument("-i", "--input", required=True, help="binary matrix")
    p_stat.add_argument("-c", "--codeframe", required=True, help="codeframe YAML")
    p_stat.add_argument("--weight", help="weight column for weighted penetration")
    p_stat.add_argument("-o", "--output", help="write table to file "
                        "(.csv/.tsv/.parquet); otherwise printed to stdout")
    p_stat.add_argument("--labels", action="store_true",
                        help="expect label-based indicator names (see convert)")
    p_stat.set_defaults(func=_cmd_stats)

    # decode ------------------------------------------------------------------
    p_dec = sub.add_parser("decode", help="inverse: binary matrix back to compact")
    _common_flags(p_dec)
    p_dec.add_argument("-i", "--input", required=True, help="binary matrix")
    p_dec.add_argument("-c", "--codeframe", required=True, help="codeframe YAML")
    p_dec.add_argument("-o", "--output", required=True,
                       help="compact output (.csv/.tsv/.parquet/.xlsx)")
    p_dec.add_argument("--labels", action="store_true",
                       help="expect label-based indicator names (see convert)")
    p_dec.set_defaults(func=_cmd_decode)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    log = configure_logging(verbose=args.verbose, quiet=args.quiet)
    return args.func(args, log)


if __name__ == "__main__":
    sys.exit(main())
