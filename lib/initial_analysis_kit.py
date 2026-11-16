"""The analysis stages of the initial-analysis notebooks, as plain functions.

`initial-analysis.py` runs each of them through `record(...)` (so a stage and the widget values that drove it become one recorded
step); `initial-review.py` replays the stored results. They are ports of the cells of the exploratory `initial-analysis` notebook,
working on the enriched Dhana LoanApplication log (colon-free column names, see `scripts/xes_to_parquet.py`). None of them changes
its input.

`lib/` is put on `sys.path` by the notebooks, so the sibling helper modules are imported flat.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import data_quality_util as dqu
import temporal_characteristics_util as tcu

CASE_ID = "case_concept_name"
ACTIVITY = "concept_name"
TIMESTAMP = "time_timestamp"
DHANA = "data/dhana-loan-application.parquet"
HISTORY_NAME = "Dhana loan application initial analysis"

# a step that needs these can never lose them to the "constant column" rule (a log with one case has a constant case id)
_PROTECTED = (CASE_ID, ACTIVITY, TIMESTAMP)


def _is_timestamp(series: pd.Series) -> bool:
    return isinstance(series.dtype, pd.DatetimeTZDtype) or pd.api.types.is_datetime64_dtype(series)


def load_event_log(path) -> pd.DataFrame:
    return pd.read_parquet(Path(path))


def timestamp_formats(log: pd.DataFrame) -> pd.DataFrame:
    """The format of each timestamp column, where the recorded data tells it unambiguously."""
    rows = []
    for col in [c for c in log.columns if _is_timestamp(log[c])]:
        result = tcu.infer_timestamp_format_from_column(log[col])
        rows.append({
            "Timestamp column": col,
            "Status": result["status"],
            "Format": tcu.format_to_human(result["format"]),
            "Example": tcu.get_example_timestamp(log[col], result["format"]),
            "Pattern": result["format"],
        })
    return pd.DataFrame(rows)


def time_frame(log: pd.DataFrame, case_id: str, completion_time: str, default_case_count: int = 1500) -> dict:
    """What the time-frame slider is built from: `start` of the log, the `unit` ('D', or 'h' for logs shorter than two days), the
    slider's `stop` and the `default` end that covers the first `default_case_count` cases."""
    bounds = tcu.get_case_time_bounds(log, case_id, completion_time)
    start, last = bounds["min"].min(), bounds["max"].max()
    unit = "D" if (last - start) >= pd.Timedelta(days=2) else "h"
    length = pd.Timedelta(1, unit)
    default_end = tcu.get_end_time_of_nth_case(bounds, default_case_count)
    return {
        "start": start,
        "unit": unit,
        "stop": int((last - start) / length) + 1,
        "default": int((default_end - start) / length) + 1,
    }


def initialize_log(
    log: pd.DataFrame, timezone: str, granularity: str | None, enforce_order: bool, window: tuple, case_id: str, completion_time: str
) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    """Time zone, granularity, time frame, constant/empty columns, duplicates, optional global ordering, folded data.

    `window` is the slider's (from, to) in the units of `time_frame`. Returns the initialized log, what was done (one line each) and
    one kept instance per group of duplicate events."""
    out = log.copy()
    messages: list[str] = []
    frame = time_frame(out, case_id, completion_time)

    for col in out.columns:
        if isinstance(out[col].dtype, pd.DatetimeTZDtype):
            out[col] = out[col].dt.tz_convert(timezone)
            messages.append(f"Converted column '{col}' to timezone {timezone}")

    if granularity is not None:
        if granularity not in tcu._FREQ_ALIASES:
            messages.append(f"Granularity normalization to '{granularity}' is currently not supported.")
        else:
            for col in [c for c in out.columns if _is_timestamp(out[c])]:
                rounded = out[col].dt.round(tcu._FREQ_ALIASES[granularity])
                messages.append(f"Rounded {int((rounded != out[col]).sum())}/{len(out)} values in '{col}' to the nearest {granularity}")
                out[col] = rounded

    start = frame["start"] + pd.Timedelta(window[0], frame["unit"])
    end = frame["start"] + pd.Timedelta(window[1], frame["unit"])
    cases_before = out[case_id].nunique()
    out = tcu.filter_cases_within_window(out, case_id, completion_time, start, end)
    messages.append(f"Time frame {start} to {end}: kept {out[case_id].nunique()} of {cases_before} cases ({len(out)} events)")
    if out.empty:
        return out.assign(folded_data=pd.Series(dtype=object)), messages, dqu.summarize_duplicate_events(out)

    filled = [c for c in out.columns if out[c].notna().all()]
    constant = [c for c in filled if out[c].nunique() <= 1 and c not in _PROTECTED and c not in (case_id, completion_time)]
    for col in constant:
        values = out[col].unique()
        messages.append(f"Dropped constant column '{col}' with value: {values[0] if len(values) else None}")
    out = out.drop(columns=constant)
    empty = [c for c in out.columns if c not in filled and out[c].notna().sum() == 0]
    for col in empty:
        messages.append(f"Dropped empty column '{col}'")
    out = out.drop(columns=empty)
    inconsistent = [c for c in out.columns if c not in filled and c not in empty]

    duplicates = dqu.summarize_duplicate_events(out)
    if not duplicates.empty:
        before = len(out)
        out = dqu.remove_duplicate_events(out)
        messages.append(f"Removed {before - len(out)} duplicate events in {len(duplicates)} groups of identical events")

    if enforce_order:
        out = out.assign(original_order=range(len(out))).sort_values(by=[completion_time, "original_order"]).reset_index(drop=True)
        assert out[completion_time].is_monotonic_increasing
        messages.append("All events in the log are now globally ordered.")

    records = out[inconsistent].to_dict("records") if inconsistent else [{} for _ in range(len(out))]
    out["folded_data"] = pd.Series([{k: v for k, v in r.items() if pd.notna(v)} or None for r in records], index=out.index, dtype=object)
    return out, messages, duplicates


def ordering_summaries(log: pd.DataFrame, case_id: str, completion_time: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    return tcu.analyze_event_ordering(log, case_id, completion_time)


def classify_attributes(log: pd.DataFrame, case_id: str, activity: str, completion_time: str) -> dict:
    """Mandatory, standard (filled by every activity), case-level and per-activity attributes of the log."""
    mandatory = [case_id, activity, completion_time]
    stats = log[activity].value_counts()
    attrs = log.drop(columns=["folded_data"], errors="ignore")
    counts = attrs.groupby(activity).count().reindex(stats.index)
    standard = [c for c in counts.columns if (counts[c] != 0).all() and c not in mandatory]
    schema = {
        a: [c for c in counts.columns if counts.loc[a, c] != 0 and c not in mandatory + standard] for a in stats.index
    }
    per_case = attrs.drop(columns=[case_id]).groupby(attrs[case_id]).nunique()
    case_features = [c for c in per_case.columns if per_case[c].max() <= 1]
    return {
        "mandatory": mandatory,
        "standard": standard,
        "case_features": case_features,
        "activity_schema": schema,
        "activity_list": list(stats.index),
        "activity_stats": stats,
    }


def build_case_log(
    log: pd.DataFrame, case_id: str, activity: str, completion_time: str, case_features: list, enrichment_code: str | None = None
) -> pd.DataFrame:
    """One row per case: start, end, number of events and the case-level attributes; then the student's enrichment code, if any,
    run with `case_log` (and `pd`, `event_log`) in scope. An error in that code propagates."""
    grouped = log.groupby(case_id)
    cases = grouped.agg(
        start_time=(completion_time, "first"), end_time=(completion_time, "last"), no_of_events=(activity, "count")
    )
    extra = [c for c in case_features if c not in cases.columns and c != "folded_data"]
    if extra:
        folded = grouped[extra].first()
        for col in extra:
            cases[col] = folded[col]
    if enrichment_code:
        scope = {"case_log": cases, "pd": pd, "event_log": log}
        exec(enrichment_code, scope)
        cases = scope["case_log"]
    return cases


def schema_views(
    log: pd.DataFrame, case_id: str, activity: str, mandatory: list, standard: list, activity_stats: pd.Series
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`(schema_usages, partial_schema_usages)`: per activity how many events fill each attribute, its incidence, its local
    attributes and the values it is missing; and the attributes shared by some but not all activities."""
    counts = (
        log.drop(columns=["folded_data", activity], errors="ignore").groupby(log[activity]).count().reindex(activity_stats.index)
    )
    usages = counts.copy()
    usages["incidence"] = usages[case_id]
    non_schema = list(mandatory) + list(standard) + ["incidence"]
    extra = [c for c in counts.columns if c not in non_schema]
    usages["extra_schema"] = [
        {c: int(v) for c, v in row.items() if v != 0} for row in counts[extra].to_dict("records")
    ] if extra else [{} for _ in range(len(usages))]
    usages["local_attributes"] = usages["extra_schema"].apply(lambda d: sorted(d))
    usages["missing_values"] = [
        {c: v - inc for c, v in schema.items() if v - inc != 0} for schema, inc in zip(usages["extra_schema"], usages["incidence"])
    ]
    partial_cols = [c for c in counts.columns if 2 <= (counts[c] != 0).sum() < len(counts)]
    return usages, usages[partial_cols]


# --- views of the log ----------------------------------------------------------------------------------------------------------


def timestamp_components(log: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """How precise the timestamps are and which of their parts are constant (every timestamp column of the log)."""
    return tcu.analyze_timestamp_components(log)


def select_timestamp_component(summary: pd.DataFrame, prefixes: pd.DataFrame, column: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The component analysis and the constant prefixes of one timestamp column."""
    pick = lambda frame: frame[frame["Timestamp column"] == column].drop(columns="Timestamp column")  # noqa: E731
    return pick(summary), pick(prefixes)


def event_views(log: pd.DataFrame, found: dict) -> dict:
    """The event tables of the events view: `global` (mandatory and standard attributes) and `inspection` (the same, with the
    attributes that only some activities fill folded into one column). Case-level attributes are left to the case log."""
    columns = [c for c in found["mandatory"] + found["standard"] if c not in found["case_features"]]
    return {"global": log[columns], "inspection": log[columns + ["folded_data"]]}


def local_attribute_view(log: pd.DataFrame, activities: list, found: dict, hide_case_features: bool) -> pd.DataFrame:
    """The events of the selected activities with the attributes common to all their schemas."""
    if not activities:
        return log.iloc[0:0][found["mandatory"]]
    common = set(found["activity_schema"].get(activities[0], []))
    for name in activities[1:]:
        common &= set(found["activity_schema"].get(name, []))
    columns = [c for c in sorted(common) if c != "folded_data" and not (hide_case_features and c in found["case_features"])]
    return log[log[found["mandatory"][1]].isin(activities)][found["mandatory"] + columns]


# --- reading what was recorded -------------------------------------------------------------------------------------------------


def params_at(adapter, state_id: str | None, step_name: str) -> dict | None:
    """The arguments of the last step called `step_name` up to (and including) `state_id`, or in the whole history when
    `state_id` is None. Lets a notebook that is opened again show its widgets as they were left, and lets a reviewer see the widget
    values that produced a result."""
    found = None
    for node_id, node in adapter.get_tree().nodes.items():
        if node.operation.name == step_name:
            found = dict(node.params)
        if state_id is not None and node_id == state_id:
            break
    return found


def step_state_id(adapter, state_id: str | None, step_name: str) -> str | None:
    """The state that the last step called `step_name` produced, up to (and including) `state_id`; None when there is none."""
    found = None
    for node_id, node in adapter.get_tree().nodes.items():
        if node.operation.name == step_name:
            found = node_id
        if state_id is not None and node_id == state_id:
            break
    return found


def _stored_steps(rt) -> list[dict]:
    """The steps of the stored history, oldest first (the history is linear: each state has one step after it)."""
    steps, at, seen = [], rt._root_state_id, set()
    while at not in seen:
        seen.add(at)
        children = rt.storage.load_child_steps(at)
        if not children:
            break
        steps.append(children[-1])
        at = children[-1]["output_state_id"]
    return steps


def analyst_recorder(rt, adapter):
    """`(record, state_of)` for someone doing the analysis: `record(targets, function, *args, name=None, **kwargs)` runs the step and
    stores it, so that an annotation can be attached to what it produced and the analysis can be replayed step by step.

    When a notebook is opened again it runs from the top, and its widgets come back as they were left. A call that is identical to
    the latest stored step of that name is then not stored a second time (it still runs, and what it produced is the stored
    step's), once per step name. The first call that differs, or a second call of the same name, is the analyst's own work: from
    then on every call is stored, so a step repeated on purpose is a new step (the tracker's fingerprint keeps only 200 characters of
    an argument, so a long argument that changed must never be mistaken for a stored one).
    """
    from tracker.runtime import _param_fingerprint

    latest = {step["func_name"]: step for step in _stored_steps(rt)}
    produced: dict = {}
    matched: set = set()  # step names already matched to their stored step: a second call of that name is new work

    def record(targets, function, *args, name=None, **kwargs):
        label = name or function.__name__
        stored = latest.get(label)
        if label not in matched and stored is not None and stored["param_fingerprint"] == _param_fingerprint(list(args), kwargs):
            matched.add(label)
            result = function(*args, **kwargs)
            for target in targets:
                produced[target] = stored["output_state_id"]
            return result
        matched.update(latest)  # the analyst has moved on: nothing is matched to the stored history from here
        result = rt.trace_step(
            func=function, func_name=label, raw_line=f"{', '.join(targets)} = {label}(...)",
            args=list(args), kwargs=kwargs, targets=list(targets),
        )
        for target in targets:
            produced[target] = rt._current_state_id
        return result

    def state_of(target):
        """The recorded state that produced `target`: what an annotation about it is attached to."""
        return produced.get(target) or (adapter.latest_state_id() if adapter is not None else None) or "analysis"

    return record, state_of
