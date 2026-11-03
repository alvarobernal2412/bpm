"""The code the two BPI Challenge 2017 notebooks share: the steps of the analysis, the key box, and how a step is recorded.

`student-notebook.py` and `model-solution.py` import this module; so does `tools/make_model_solution.py`, which records the
model analysis. Keeping the steps here means the notebook a student works in, the tutorial that replays a solution and the
script that records it can never drift apart: they call the same functions under the same names.
"""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import anywidget
import lcm
import pandas as pd
import traitlets

ACTIVITY = "concept:name"
CASE_ID = "case:concept:name"
TIMESTAMP = "time:timestamp"

HISTORY_NAME = "BPI 2017 Task 1 with LCM maps"  # what a student's work is stored under
SOLUTION_HISTORY_NAME = "BPI 2017 Task 1, model solution"

_FAMILIES = {"A_": "Application", "O_": "Offer", "W_": "Workflow"}


class NotStored:
    """Stands in for a value that was recorded but left out of a provenance zip to keep it small."""

    def __repr__(self):
        return "<not stored>"


def session_folder(key: str) -> Path:
    """Where one student's work lives while the notebook runs: a folder per key, so students who share a hosted notebook
    never write into each other's provenance."""
    return Path(tempfile.gettempdir()) / "bpm-provenance" / hashlib.sha256(key.encode()).hexdigest()[:16]


class KeyBox(anywidget.AnyWidget):
    """A field for the student's key. The key is kept in this browser (not in the notebook, which a fork copies)."""

    key = traitlets.Unicode("").tag(sync=True)
    _esm = """
    export default {
      render({ model, el }) {
        const STORE = "bpm-course-key";
        const row = document.createElement("div");
        row.style.cssText = "display:flex;gap:8px;align-items:center;flex-wrap:wrap";
        const input = document.createElement("input");
        input.type = "password";
        input.autocomplete = "off";
        input.placeholder = "Paste your key here";
        input.style.cssText = "flex:1 1 320px;padding:8px 10px;font-size:14px;border:1px solid #94a3b8;border-radius:6px";
        const start = document.createElement("button");
        start.textContent = "Start";
        start.style.cssText = "padding:8px 18px;font-size:14px;border:0;border-radius:6px;background:#0ea5e9;color:#fff;cursor:pointer";
        const label = document.createElement("label");
        label.style.cssText = "font-size:12px;color:#64748b;display:flex;gap:4px;align-items:center";
        const remember = document.createElement("input");
        remember.type = "checkbox";
        remember.checked = true;
        label.append(remember, "Remember on this computer");
        const other = document.createElement("button");
        other.textContent = "Use another key";
        other.style.cssText = "display:none;padding:4px 10px;font-size:12px;border:1px solid #94a3b8;border-radius:6px;background:transparent;cursor:pointer";
        const keep = (value) => {
          try { if (value && remember.checked) localStorage.setItem(STORE, value); else localStorage.removeItem(STORE); } catch (e) {}
        };
        const send = (value) => {
          model.set("key", value);
          model.save_changes();
          other.style.display = value ? "inline-block" : "none";
        };
        start.onclick = () => { const v = input.value.trim(); if (v) { keep(v); send(v); } };
        input.onkeydown = (e) => { if (e.key === "Enter") start.onclick(); };
        other.onclick = () => { try { localStorage.removeItem(STORE); } catch (e) {} input.value = ""; send(""); };
        row.append(input, start, label, other);
        el.append(row);
        let stored = "";
        try { stored = localStorage.getItem(STORE) || ""; } catch (e) {}
        if (stored) { input.value = stored; send(stored); }
      },
    };
    """


# --- the steps of the analysis ------------------------------------------------------------------------------------------------
# Each is a plain function. A notebook runs it through record(), which stores its inputs and outputs as one step.


_locate = None


def use_project_files(locate) -> None:
    """Tell the kit how to find the project's files: `locate("data/bpi2017.parquet")` returns a path. A notebook on a hosted
    platform, where only the notebook file is delivered, passes the function that downloads them."""
    global _locate
    _locate = locate


def load_event_log(name: str) -> pd.DataFrame:
    """The BPI 2017 log (a Parquet copy of BPI_Challenge_2017.xes, all 19 columns). `name` is its place in the project, such as
    `data/bpi2017.parquet`: it is what gets recorded, so a recorded analysis names the file, not a folder of somebody's computer."""
    path = _locate(name) if _locate else Path(__file__).resolve().parent / name
    return pd.read_parquet(path)


def summarise_log(log: pd.DataFrame) -> dict:
    return {
        "cases": int(log[CASE_ID].nunique()),
        "events": len(log),
        "activities": int(log[ACTIVITY].nunique()),
        "columns": log.shape[1],
    }


def family_of(activity: str) -> str:
    """Application (A_), Offer (O_) or Workflow (W_), by the start of the activity name."""
    return _FAMILIES.get(activity[:2], "Other")


def activity_overview(log: pd.DataFrame) -> pd.DataFrame:
    """Every activity with its family, how many events it has and in how many cases it occurs."""
    grouped = log.groupby(ACTIVITY)
    table = pd.DataFrame({"events": grouped.size(), "cases": grouped[CASE_ID].nunique()})
    table["% of cases"] = (table["cases"] / log[CASE_ID].nunique() * 100).round(1)
    table.insert(0, "family", [family_of(name) for name in table.index])
    order = {name: i for i, name in enumerate(_FAMILIES.values())}
    table = table.rename_axis("activity").reset_index()
    return table.sort_values(["family", "events"], key=lambda c: c.map(order) if c.name == "family" else -c).reset_index(drop=True)


def attribute_overview(log: pd.DataFrame) -> pd.DataFrame:
    """Every column of the log: how many events have a value for it, and how many different values there are."""
    filled = log.notna().sum()
    return pd.DataFrame(
        {
            "events with a value": filled,
            "% of events": (filled / len(log) * 100).round(2),
            "different values": log.nunique(),
        }
    ).rename_axis("attribute").reset_index()


def log_sample(log: pd.DataFrame, rows: int) -> pd.DataFrame:
    """The first events of the log, as they are stored."""
    return log.head(rows).reset_index(drop=True)


def attribute_coverage(log: pd.DataFrame, activity: str) -> pd.DataFrame:
    """For one activity: how many of its events carry each attribute."""
    events = log[log[ACTIVITY] == activity]
    carried = events.notna().sum()
    return pd.DataFrame(
        {
            "events with a value": carried,
            "events": len(events),
            "% of events": (carried / len(events) * 100).round(2),
        }
    ).rename_axis("attribute").reset_index()




def activities_starting_with(log: pd.DataFrame, prefix: str) -> list:
    return sorted(a for a in log[ACTIVITY].unique() if a.startswith(prefix))


def case_activity_timestamp(log: pd.DataFrame) -> pd.DataFrame:
    return log[[CASE_ID, ACTIVITY, TIMESTAMP]]


def events_carrying(log: pd.DataFrame, attribute: str) -> pd.DataFrame:
    """The log reduced to the events that have a value for `attribute` (case, activity and timestamp only)."""
    return log[log[attribute].notna()][[CASE_ID, ACTIVITY, TIMESTAMP]]


def distinct_activities(log: pd.DataFrame) -> list:
    return sorted(log[ACTIVITY].unique())


def draw_map(log, activities, builder, allow_loops, show_empty, height):
    """A Linear Continuous Process Mapper map of `log` over `activities`."""
    figure, metadata = lcm.get_service(log).generate(
        activities=activities,
        map_type=builder,
        allow_loops=allow_loops,
        visualize_empty_cases=show_empty,
    )
    figure.update_layout(height=height)
    return figure, metadata










# --- recording ---------------------------------------------------------------------------------------------------------------------
# Every analysis step goes through record(targets, function, *args). The analyst's record() runs the step and records it. The
# reviewer's record() runs nothing: it hands back what that step produced at the step the reviewer is on, so each cell shows its
# own output as it was then, like a replay.


def analyst_recorder(rt, adapter):
    """`(record, state_of)` for someone doing the analysis.

    The notebook runs again from the top whenever the page is opened or the kernel restarts. That run repeats the stored history
    from its first step, and those steps are not recorded a second time: a call is skipped only while it is the very next step of
    the stored history (same name, same inputs). The first call that is not ends this, and from then on every step is recorded, so
    a step a student repeats on purpose is a new step. `replay_stored=False` marks a step a student asks for (a click): it is
    always recorded.
    """
    from tracker.runtime import _param_fingerprint

    produced = {}  # target name -> the state of the step that produced it
    replay = {"on": True, "at": rt._root_state_id, "head": rt._current_state_id}

    def _stored_step(label, args, kwargs):
        try:
            fingerprint = _param_fingerprint(list(args), kwargs)
            for child in rt.storage.load_child_steps(replay["at"]):
                if child["func_name"] == label and child["param_fingerprint"] == fingerprint:
                    return child
        except Exception:
            pass  # when in doubt, record the step
        return None

    def record(targets, function, *args, name=None, replay_stored=True, **kwargs):
        label = name or function.__name__
        stored = _stored_step(label, args, kwargs) if replay["on"] and replay_stored else None
        if stored is not None:
            result = function(*args, **kwargs)
            replay["at"] = rt._current_state_id = stored["output_state_id"]
        else:
            if replay["on"]:
                replay["on"] = False
                rt._current_state_id = replay["head"]  # new work goes after the end of the stored history
            result = rt.trace_step(
                func=function,
                func_name=label,
                raw_line=f"{', '.join(targets)} = {label}(...)",
                args=list(args),
                kwargs=kwargs,
                targets=list(targets),
            )
        for target in targets:
            produced[target] = rt._current_state_id
        return result

    def state_of(target):
        """The recorded state that produced `target`: what a note about it is attached to."""
        return produced.get(target) or adapter.latest_state_id() or "analysis"

    return record, state_of


def reviewer_recorder(snap, mo):
    """`(record, state_of)` for someone reading a recorded analysis. `mo` is marimo: a cell whose step has not happened yet at the
    step the reviewer is on stops there and says so."""

    def record(targets, function, *args, name=None, replay_stored=True, **kwargs):
        for target in targets:
            mo.stop(snap.status(target) == "not_computed", mo.md(snap.missing(target)))
        values = [snap.get(t) if snap.status(t) == "ok" else NotStored() for t in targets]
        return values[0] if len(values) == 1 else tuple(values)

    def state_of(target):
        # The step the reviewer is on is the id of what that step produced, so the panel can flash it when the reviewer steps to it.
        # What an earlier step produced keeps a different id and is not flashed.
        if getattr(snap, "produced_here", lambda _: False)(target):  # an older marimo-pmprov has no highlight of steps
            return snap.state_id
        return f"{snap.state_id}-earlier" if snap.state_id else "analysis"

    return record, state_of
