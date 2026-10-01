#!/usr/bin/env bash
#
# build_history_v3.sh — turn the v0.3.0 changes into a clean sequence of
# feature commits ON TOP OF your existing v0.2.0 history.
#
# This is a local helper, NOT part of the repo. It stages specific files per
# commit (never itself), so each commit is a coherent, self-contained change
# with a real diff. Every commit is buildable and green. All commits are dated
# now — do NOT backdate to fake a longer timeline.
#
# Prerequisite: you are in the repo root, your v0.1.0 + v0.2.0 commits are
# already there (git log shows them), and these v0.3.0 files are in place.
#
# Usage:
#   bash build_history_v3.sh
#
# Afterwards:
#   git log --oneline
#   git push                 # normal push — see COMMIT_GUIDE.md
#   rm build_history_v3.sh COMMIT_GUIDE.md

set -euo pipefail

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: not inside a git repository. See COMMIT_GUIDE.md."
  exit 1
fi
if git diff --quiet && git diff --cached --quiet; then
  echo "error: no changes to commit. Are the v0.3.0 files in place?"
  exit 1
fi

commit () {
  local msg="$1"; shift
  git add -- "$@"
  git commit -m "$msg" >/dev/null
  echo "  committed: $msg"
}

echo "Building v0.3.0 commit sequence..."

commit "feat: net/combination variables

A multi-response question can define nets in the codeframe — named
OR-combinations of its codes emitted as extra 0/1 columns (e.g.
Q3_net_any_premium). Nets inherit the question's missing-data policy." \
  src/compact2binary/nets.py \
  src/compact2binary/codeframe.py \
  src/compact2binary/convert.py \
  config/codeframe.example.yaml \
  tests/test_nets.py \
  examples/sample_data/sample_binary.csv

commit "feat: Excel (.xlsx) table I/O

Read and write .xlsx / .xlsm alongside CSV/TSV/Parquet, chosen by file
extension. Requires the excel extra (openpyxl)." \
  src/compact2binary/tables.py \
  tests/test_xlsx.py

commit "feat: decode — inverse binary to compact transform

Add a decode subcommand and decode() API that rebuild compact (delimited)
storage from a binary matrix, making the pipeline round-trippable and able to
feed tools that expect compact input." \
  src/compact2binary/decode.py \
  src/compact2binary/cli.py \
  tests/test_decode.py

commit "docs: release v0.3.0

Export the new nets and decode API, bump the version to 0.3.0, add the excel
extra, update the CHANGELOG, README, overview and CI smoke test." \
  src/compact2binary/__init__.py \
  pyproject.toml \
  CHANGELOG.md \
  README.md \
  docs/OVERVIEW.md \
  .github/workflows/ci.yml

echo ""
echo "Done. Recent history:"
git log --oneline | head -12
