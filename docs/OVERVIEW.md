# Overview and design notes

This document is about why the tool exists, the context it came out of, and the decisions behind it. The [README](../README.md) covers how to use it.

## Background

In survey research, multi-response questions ("select all the brands you've bought", "which features do you use") don't have one answer per respondent. They get stored in a compact form that records only what was picked:

- **Multi-column ("mentions"):** several columns, each holding one selected code, blank-padded. Someone who picked three brands fills three columns and leaves the rest empty.
- **Delimited:** a single column holding the selected codes joined together, for example `"1;3;7"`.

Compact storage is efficient and it matches how survey platforms export. The problem is that almost every downstream task (cross-tabulation, banner tables, penetration and overlap analysis, modelling) needs the binary form instead: one 0/1 column per possible answer. The expansion looks trivial, but in practice it is easy to get wrong. You repeat it across many questions and waves, and a quiet mistake (a dropped mention slot, an unrecognised code, a mis-mapped column) can travel all the way into a client deliverable before anyone notices.

This is a generalised, clean-room version of an automation I originally wrote to do that expansion reliably in a production survey-processing workflow. The technique itself is standard industry practice. I rebuilt it from the concept against synthetic data so I could share it publicly.

## Design principles

**1. The codeframe is the only place survey specifics live.**
The conversion engine knows nothing about any particular survey. Question ids, storage layout, column names, codes, labels and missing-data policy all come from a YAML codeframe. That is what lets one engine work for every survey, and it matches how survey metadata is actually managed in practice, kept separate from the processing logic.

**2. Convert and validate are independent.**
The validator doesn't trust the converter. It re-parses the original compact input and checks the produced matrix against it, so it can actually catch conversion bugs instead of waving them through. If your QC shares code with the thing it is checking, it tends to share the same blind spots.

**3. Fail loudly, never silently.**
Unknown codes and count mismatches are errors with a non-zero exit code, so they can stop a CI run or a scheduled job. Unparseable tokens come through as warnings rather than getting swallowed. The one thing the pipeline never does is quietly produce a wrong matrix that looks fine.

**4. Keep everything you didn't ask it to change.**
IDs, weights, single-response questions and open-ends pass through in their original order. A conversion tool that reorders or drops columns just creates more work, so this one only touches the multi-response questions named in the codeframe.

**5. Anyone can run it straight away.**
The synthetic data generator means the repo isn't a code sample you have to picture running. It's a pipeline you can run in under a minute, with the QC showing the output is correct.

## Key decisions and trade-offs

**Output column naming.** Indicators follow `{qid}_{code}` by default, and it's configurable. The source mention columns in the sample data are named `Q3_m1…` rather than `Q3_1…` so the inputs and the generated outputs can't collide. It's a small convention that avoids a lot of confusion.

**Missing data.** A blank multi-response answer is ambiguous. It can mean "was asked, selected nothing" or "was never asked / off-base". Those need to become `0` and `NaN` respectively, because collapsing them together corrupts penetration bases later on. So the codeframe has a per-question `missing_policy` (`zero` or `nan`) instead of the tool guessing.

**Code parsing is forgiving about format, strict about meaning.** Cells like `"3.0"` or `" 3 "` parse to code `3`. Genuinely non-integer tokens (`"2.5"`, `"other"`) are rejected and reported, never coerced. Formatting noise from CSV round-trips shouldn't break a run, but the tool should never invent data.

**Nullable integer indicators.** Indicator columns use pandas' `Int8`, so the deliberate `NaN` (off-base) case can be stored without upcasting the whole matrix to float. That keeps the output compact and the 0/1 meaning intact.

## Clean-room and confidentiality approach

I produced this repo by reimplementing the technique against synthetic data, not by sanitising a real working file. That was a deliberate choice:

- Scrubbing a real file risks leaving proprietary content behind, and the original still sits in Git history anyway.
- A fresh implementation driven by `faker` output carries no client data at all, so there is nothing to leak.
- Notebook cell outputs, cached datasets, environment paths and connection metadata are the usual ways work leaks when you publish it from a professional environment, and none of those exist here.

The pre-commit hooks (`gitleaks` for secret scanning, `nbstripout` to reject notebooks with outputs) enforce that on every commit.

## Shipped since 0.1.0

See [CHANGELOG.md](../CHANGELOG.md) for the detail. In short: 0.2.0 added
value-labelled output columns, an exclusive-code ("None of these") integrity
check, weighted penetration statistics (`stats`), Parquet/TSV I/O and logging.
0.3.0 added net/combination variables, a `decode` inverse transform
(binary back to compact), and Excel (`.xlsx`) I/O. These moved up from the
wishlist below into the tool itself.

## Possible extensions

- Direct readers and writers for SPSS (`.sav`).
- Automatic codeframe scaffolding from a data dictionary export.
- Categorical-dtype output for questions where the labels, not the codes, are wanted as values downstream.
- Cross-question consistency rules (for example "bought implies aware") in the validator.
