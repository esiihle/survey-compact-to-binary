# Overview & design notes

This document explains *why* the tool exists, the context it came from, and the design decisions behind it. The [README](../README.md) covers *how* to use it.

## Background

In survey research, **multi-response** questions — "select all brands you've bought", "which features do you use" — don't have a single answer per respondent. They're stored in a *compact* form that records only what was picked:

- **Multi-column ("mentions"):** several columns, each holding one selected code, blank-padded. A respondent who picked three brands fills three columns; the rest are empty.
- **Delimited:** a single column holding the selected codes joined together, e.g. `"1;3;7"`.

Compact storage is efficient and matches how survey platforms export, but almost every downstream task — cross-tabulation, banner tables, penetration/overlap analysis, modelling — needs the **binary** form: one 0/1 column per possible answer. The expansion is conceptually trivial and operationally treacherous: it's repeated across many questions and waves, and a quiet mistake (a dropped mention slot, an unrecognised code, a mis-mapped column) propagates silently into a client deliverable.

This tool is a generalised, clean-room version of an automation originally built to do that expansion reliably in a production survey-processing workflow. The technique is standard industry practice; this implementation was rebuilt from the concept against synthetic data specifically so it could be shared publicly.

## Design principles

**1. The codeframe is the only place survey specifics live.**
The conversion engine knows nothing about any particular survey. Question ids, storage layout, column names, codes, labels, and missing-data policy all come from a YAML codeframe. This is what makes one engine work for every survey, and it mirrors how survey metadata is actually managed — separately from the processing logic.

**2. Convert and validate are independent.**
The validator does not trust the converter. It re-parses the original compact input and checks the produced matrix against it, so it can genuinely catch conversion bugs rather than rubber-stamping them. QC that shares code with the thing it's checking tends to share the thing's blind spots.

**3. Fail loudly, never silently.**
Unknown codes and count mismatches are errors with a non-zero exit code, so they can gate a CI run or a scheduled job. Unparseable tokens are surfaced as warnings rather than swallowed. The one thing the pipeline never does is quietly produce a plausible-looking but wrong matrix.

**4. Preserve everything you didn't ask to change.**
IDs, weights, single-response questions, and open-ends pass through in original order. A conversion tool that reorders or drops columns creates work; this one changes only the multi-response questions named in the codeframe.

**5. Runnable by anyone, immediately.**
The synthetic data generator means the repository is not a code sample you have to imagine running — it's a pipeline you can execute in under a minute, with QC proving the output is correct.

## Key decisions and trade-offs

**Output column naming.** Indicators follow `{qid}_{code}` by default (configurable). Source mention columns in the sample data are named `Q3_m1…` rather than `Q3_1…` so that inputs and generated outputs can never collide — a small convention that removes a whole class of confusion.

**Missing data.** A blank multi-response answer is ambiguous: it can mean "was asked, selected nothing" or "was never asked / off-base". These must become `0` and `NaN` respectively, because collapsing them corrupts penetration bases downstream. The codeframe exposes a per-question `missing_policy` (`zero` | `nan`) rather than guessing.

**Code parsing is forgiving about format, strict about meaning.** Cells like `"3.0"` or `" 3 "` parse to code `3`; genuinely non-integer tokens (`"2.5"`, `"other"`) are rejected and reported, never coerced. Surface-formatting noise from CSV round-trips shouldn't break a run, but invented data is never acceptable.

**Nullable integer indicators.** Indicator columns use pandas' `Int8` so the deliberate `NaN` (off-base) case is representable without upcasting the whole matrix to float — keeping the output compact and the 0/1 semantics honest.

## Clean-room / confidentiality approach

This repo was produced by **reimplementing the technique against synthetic data**, not by sanitising a real working file. That choice is deliberate:

- Scrubbing a real file risks residual proprietary content and leaves the original in Git history regardless.
- A fresh implementation driven by `faker` output carries no client data by construction — there is nothing to leak.
- Notebook cell outputs, cached datasets, environment paths, and connection metadata — the usual leakage vectors when publishing work from a professional environment — simply never exist here.

The included pre-commit hooks (`gitleaks` for secret scanning, `nbstripout` to reject notebooks with outputs) enforce that discipline on every commit.

## Shipped since 0.1.0

See [CHANGELOG.md](../CHANGELOG.md) for detail. In brief: 0.2.0 added
value-labelled output columns, an exclusive-code ("None of these") integrity
check, weighted penetration statistics (`stats`), Parquet/TSV I/O, and logging.
0.3.0 added net/combination variables, a `decode` inverse transform
(binary → compact), and Excel (`.xlsx`) I/O. These moved from the wishlist
below into the tool proper.

## Possible extensions

- Direct readers/writers for SPSS (`.sav`).
- Automatic codeframe scaffolding from a data dictionary export.
- Categorical-dtype output for questions where labels, not codes, are wanted as values downstream.
- Cross-question consistency rules (e.g. "bought ⇒ aware") in the validator.
