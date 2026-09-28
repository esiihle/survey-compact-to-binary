#!/usr/bin/env bash
#
# build_history_v2.sh — turn the v0.2.0 changes into a clean sequence of
# feature commits ON TOP OF your existing v0.1.0 commit.
#
# This is a local helper, NOT part of the repo. It stages specific files per
# commit (never itself), so each commit is a coherent, self-contained change
# with a real diff. Every commit is buildable and green. All commits are dated
# now — which is exactly how a portfolio project built over a weekend looks.
# Do NOT backdate commits to fake a longer timeline; that is the thing that
# reads as dishonest if anyone checks.
#
# Prerequisite: you are in the repo root, the v0.1.0 commit is already made
# (git log shows it), and these v0.2.0 files are in place (unstaged).
#
# Usage:
#   bash build_history_v2.sh
#
# Afterwards:
#   git log --oneline        # review the history
#   git push -u origin main  # publish
#   rm build_history_v2.sh COMMIT_GUIDE.md   # remove the helpers

set -euo pipefail

# --- sanity checks ---------------------------------------------------------
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: not inside a git repository."
  echo "  First lay down v0.1.0 and commit it (see COMMIT_GUIDE.md), then re-run."
  exit 1
fi
if git diff --quiet && git diff --cached --quiet; then
  echo "error: no changes to commit. Are the v0.2.0 files in place?"
  exit 1
fi

commit () {
  local msg="$1"; shift
  git add -- "$@"
  git commit -m "$msg" >/dev/null
  echo "  committed: $msg"
}

echo "Building v0.2.0 commit sequence..."

commit "feat: value-labelled indicator columns

Add a {label} placeholder to the output-name template (slugified answer
label) so indicators can be named Q3_krunch instead of Q3_4. Naming is
centralised in a new util.format_indicator helper. Default template is
unchanged, so existing codeframes are unaffected." \
  src/compact2binary/util.py \
  src/compact2binary/convert.py \
  tests/test_labels.py

commit "feat: exclusive-code integrity check

A multi-response question can declare exclusive codes (e.g. 'None of
these'); the validator flags any respondent who selects an exclusive code
alongside other codes. Example codeframe and synthetic generator updated
to include a realistic exclusive code." \
  src/compact2binary/codeframe.py \
  src/compact2binary/validate.py \
  config/codeframe.example.yaml \
  scripts/generate_synthetic_data.py \
  tests/test_exclusive.py \
  examples/sample_data/sample_compact.csv \
  examples/sample_data/sample_binary.csv

commit "feat: penetration/frequency statistics

Add penetration() and a stats engine that computes per-code selection
counts and percentages from a binary matrix, weighted when a weight column
is supplied, with off-base (NaN) respondents excluded from the base." \
  src/compact2binary/stats.py \
  tests/test_stats.py

commit "feat: Parquet and TSV table I/O

Dispatch reads/writes on file extension so the pipeline handles .csv, .tsv
and .parquet interchangeably. Parquet is an optional extra (pyarrow)." \
  src/compact2binary/tables.py \
  tests/test_tables.py

commit "feat: logging and CLI surface for the new capabilities

Route status through logging with --verbose/--quiet, add a stats
subcommand, wire Parquet/TSV paths through read_table/write_table, and add
a --labels shortcut for readable indicator names." \
  src/compact2binary/logging_setup.py \
  src/compact2binary/cli.py

commit "docs: release v0.2.0

Export the new public API, bump the version to 0.2.0, add a CHANGELOG, and
update the README, overview, and CI smoke test for the new features." \
  src/compact2binary/__init__.py \
  pyproject.toml \
  CHANGELOG.md \
  README.md \
  docs/OVERVIEW.md \
  .github/workflows/ci.yml

echo ""
echo "Done. Recent history:"
git log --oneline | head -8
