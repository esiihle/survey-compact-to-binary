"""Generate a synthetic compact-format survey dataset.

Everything this script emits is fake. It exists so the whole pipeline can run,
be tested, and be demonstrated without touching a single real record. The
survey theme (snack brands) and every value are invented.

The output matches config/codeframe.example.yaml:

    respondent_id, weight, Q1, Q2, Q3_m1..Q3_m6, Q4

* Q1 / Q2 are single-response (a plain code per cell).
* Q3 is multi-response in multi_column storage (up to 6 mentions).
* Q4 is multi-response in delimited storage ("1;3;7").
* weight is a passthrough numeric column, untouched by the converter.

Usage::

    python scripts/generate_synthetic_data.py \
        --rows 500 --seed 42 --out data/synthetic_compact.csv

Add ``--dirty`` to inject a few controlled anomalies (an out-of-frame code and
a non-numeric token) so the validator has something to catch in demos.
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

try:
    from faker import Faker
except ImportError:  # pragma: no cover - faker is a declared dependency
    raise SystemExit(
        "faker is required: pip install -r requirements.txt"
    )

BRAND_CODES = list(range(1, 9))  # 8 fictional brands, codes 1..8
NONE_CODE = 9                     # Q3 "None of these" (exclusive)
NONE_PROB = 0.07                  # share of respondents who bought no brand
MAX_MENTIONS = 6                  # Q3 has six mention slots
AGE_CODES = [1, 2, 3, 4, 5]
REGION_CODES = [1, 2, 3, 4]


def _weighted_brand_sample(rng: random.Random) -> list[int]:
    """Pick a plausible set of purchased brands.

    Earlier codes are a little more popular, so the resulting binary matrix
    has realistic-looking uneven column sums rather than uniform noise.
    """
    weights = [9, 8, 7, 6, 5, 4, 3, 2]  # decreasing popularity by code
    chosen: list[int] = []
    for code, w in zip(BRAND_CODES, weights):
        if rng.random() < w / 12:
            chosen.append(code)
    # Everyone bought at least one brand; keep within the mention cap.
    if not chosen:
        chosen = [rng.choice(BRAND_CODES)]
    rng.shuffle(chosen)
    return chosen[:MAX_MENTIONS]


def _awareness_from_purchase(purchased: list[int], rng: random.Random) -> list[int]:
    """Awareness is a superset of purchase, plus some extra recognised brands."""
    aware = set(purchased)
    for code in BRAND_CODES:
        if code not in aware and rng.random() < 0.35:
            aware.add(code)
    return sorted(aware)


def build_rows(n: int, seed: int, dirty: bool) -> list[dict[str, str]]:
    rng = random.Random(seed)
    fake = Faker()
    Faker.seed(seed)

    rows: list[dict[str, str]] = []
    for i in range(1, n + 1):
        # A minority bought nothing -> they pick "None of these" (code 9) only,
        # which is a valid exclusive answer (not a data error).
        if rng.random() < NONE_PROB:
            purchased = [NONE_CODE]
        else:
            purchased = _weighted_brand_sample(rng)
        aware = _awareness_from_purchase(
            [c for c in purchased if c != NONE_CODE], rng
        )

        row: dict[str, str] = {
            "respondent_id": f"R{i:05d}",
            # A passthrough numeric column the converter must leave alone.
            "weight": f"{rng.uniform(0.5, 1.8):.4f}",
            "Q1": str(rng.choice(AGE_CODES)),
            "Q2": str(rng.choice(REGION_CODES)),
        }
        # Q3: one column per mention, blank-padded to MAX_MENTIONS.
        for slot in range(1, MAX_MENTIONS + 1):
            key = f"Q3_m{slot}"
            row[key] = str(purchased[slot - 1]) if slot <= len(purchased) else ""
        # Q4: delimited awareness codes.
        row["Q4"] = ";".join(str(c) for c in aware)

        # A faker touch that never reaches the pipeline, just to show the
        # generator is a real data faker and to keep rows self-describing.
        row["_note"] = fake.word()
        rows.append(row)

    if dirty and rows:
        # 1) An out-of-frame code (99) the validator should flag as unknown.
        rows[0]["Q3_m1"] = "99"
        # 2) A non-integer token the validator should count as unparseable.
        rows[1]["Q4"] = rows[1]["Q4"] + ";x"
        # 3) An exclusive-code violation: "None of these" (9) AND a real brand.
        rows[2]["Q3_m1"] = str(NONE_CODE)
        rows[2]["Q3_m2"] = "1"

    return rows


def write_csv(rows: list[dict[str, str]], out: Path) -> None:
    if not rows:
        raise SystemExit("no rows generated")
    # Stable column order matching the codeframe; drop the helper _note column.
    fieldnames = [k for k in rows[0].keys() if k != "_note"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=500, help="number of respondents")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (reproducible)")
    parser.add_argument(
        "--out", type=Path, default=Path("data/synthetic_compact.csv"),
        help="output CSV path",
    )
    parser.add_argument(
        "--dirty", action="store_true",
        help="inject a few anomalies for the validator to catch",
    )
    args = parser.parse_args(argv)

    rows = build_rows(args.rows, args.seed, args.dirty)
    write_csv(rows, args.out)
    print(f"Wrote {len(rows)} synthetic respondents -> {args.out}"
          + (" (with injected anomalies)" if args.dirty else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
