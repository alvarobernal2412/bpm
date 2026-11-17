"""Convert an XES event log to the enriched parquet the initial-analysis notebooks load.

    python -I scripts/xes_to_parquet.py <log.xes> <out.parquet>

The XES is read as a stream (the Dhana LoanApplication log is 371 MB). Trace attributes become `case:`-prefixed columns, log-level
attributes are ignored. `enrich` then makes the log notebook-friendly: colons in column names become underscores (the marimo
explorer breaks on them) and a `case_lifecycle` column ("<case id>, <lifecycle>") is added.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from xes_reader import read_xes  # noqa: E402,F401  (also the name the tests use)

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Colon-free column names and the `case_lifecycle` column."""
    out = df.copy()
    out["case_lifecycle"] = (out["case:concept:name"].astype("string") + ", " + out["lifecycle:transition"].astype("string"))
    out.columns = [c.replace(":", "_") for c in out.columns]
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    df = enrich(read_xes(argv[1]))
    df.to_parquet(argv[2], compression="zstd", index=False)
    print(f"{len(df):,} events, {df['case_concept_name'].nunique():,} cases, {df.shape[1]} columns -> {argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
