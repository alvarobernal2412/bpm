"""Read an XES event log as a table, as a stream (the Dhana LoanApplication log is 371 MB).

Every event is a row. Event attributes are columns, trace attributes become `case:`-prefixed columns (the trace's `concept:name` is
`case:concept:name`), log-level attributes are ignored, and timestamps are converted to UTC. Used by the notebooks that read an `.xes`
file directly and by `scripts/xes_to_parquet.py`.
"""
from __future__ import annotations

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


def read_xes(path: str, verbatim: bool = False) -> pd.DataFrame:
    """One row per event; trace attributes as `case:<key>` columns; log-level attributes ignored. With `verbatim` the keys are
    columns exactly as written (a log that already uses the notebooks' column names, such as `case_concept_name`) and the
    timestamp key is `time_timestamp`."""
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
            elif verbatim:
                trace_attrs[elem.attrib["key"]] = value
            elif elem.attrib["key"] == "concept:name":
                trace_attrs["case:concept:name"] = value
            else:
                trace_attrs[f"case:{elem.attrib['key']}"] = value
    df = pd.DataFrame(rows)
    stamp = "time_timestamp" if verbatim else "time:timestamp"
    for col in df.columns:
        if df[col].dtype == object and col != stamp:
            df[col] = df[col].astype("string")
    df[stamp] = pd.to_datetime(df[stamp], utc=True).astype("datetime64[us, UTC]")
    return df
