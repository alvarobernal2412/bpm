"""Convert an XES event log to the enriched parquet the initial-analysis notebooks load.

    python -I scripts/xes_to_parquet.py <log.xes> <out.parquet>

The XES is read as a stream (the Dhana LoanApplication log is 371 MB). Trace attributes become `case:`-prefixed columns, log-level
attributes are ignored. `enrich` then makes the log notebook-friendly: colons in column names become underscores (the marimo
explorer breaks on them) and a `case_lifecycle` column ("<case id>, <lifecycle>") is added.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

import pandas as pd

_TYPED = {"float": float, "int": int, "boolean": lambda v: v == "true"}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _value(kind: str, text: str):
    if kind == "date":
        return pd.Timestamp(text).tz_convert("UTC")
    if kind in _TYPED:
        return _TYPED[kind](text)
    return text


def read_xes(path: str) -> pd.DataFrame:
    """One row per event; trace attributes as `case:<key>` columns; log-level attributes ignored."""
    rows, trace_attrs, in_event, depth = [], {}, False, 0
    event: dict = {}
    for what, elem in ET.iterparse(path, events=("start", "end")):
        tag = _local(elem.tag)
        if what == "start":
            if tag == "trace":
                trace_attrs, depth = {}, 1
            elif tag == "event":
                in_event, event = True, {}
            continue
        if tag == "event":
            rows.append({**trace_attrs, **event})
            in_event = False
            elem.clear()
        elif tag == "trace":
            depth = 0
            elem.clear()
        elif depth and "key" in elem.attrib and tag in ("string", "date", "int", "float", "boolean", "id"):
            value = _value(tag, elem.attrib["value"])
            if in_event:
                event[elem.attrib["key"]] = value
            elif elem.attrib["key"] == "concept:name":
                trace_attrs["case:concept:name"] = value
            else:
                trace_attrs[f"case:{elem.attrib['key']}"] = value
    df = pd.DataFrame(rows)
    for col in df.columns:
        if df[col].dtype == object and col != "time:timestamp":
            df[col] = df[col].astype("string")
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], utc=True).astype("datetime64[us, UTC]")
    return df


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
