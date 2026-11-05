"""The code the three course notebooks share: loading the logs, drawing a map, the map controls, the key box, how a step is
recorded and how a recorded analysis is opened for reading.

`tutorial.py`, `student-notebook.py` and `model-solution.py` import this module. Keeping the steps here means that the notebook a
student works in and the notebooks that replay a recorded analysis call the same functions under the same names, so a recorded
map can always be opened again in the map explorer with the settings that drew it.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import anywidget
import pandas as pd
import traitlets

# pm4py looks up its parent process while it is imported (to spot Power BI). In "Run as app" mode on molab the notebook's parent
# does not exist (pid 0) and psutil raises, which would stop the whole notebook. Import it as a process that has a parent.
_real_getppid = os.getppid
try:
    import psutil

    psutil.Process(_real_getppid())
except Exception:
    os.getppid = os.getpid  # no parent process to look up (or no psutil, which is harmless)
try:
    import lcm
finally:
    os.getppid = _real_getppid

ACTIVITY = "concept:name"
CASE_ID = "case:concept:name"
TIMESTAMP = "time:timestamp"

# The logs of the course, by their place in the repository.
BPI2017 = "data/bpi2017.parquet"  # BPI Challenge 2017, loan applications (the tutorial and Tasks 8 to 10)

# The names the recorded analyses are stored under.
HISTORY_NAME = "BPI 2017 Tasks 8-10 with LC maps"  # a student's work, and the model solution
TUTORIAL_HISTORY_NAME = "LC maps tutorial"

# Where the reviewer notebooks find a recorded analysis when the course server does not provide it.
TUTORIAL_ZIP = "histories/tutorial.zip"
SOLUTION_ZIP = "histories/model-solution.zip"

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
    """A field for the student's key. The key is kept in this browser (not in the notebook, which a fork copies). `store` names
    where, so that a notebook for reviewers does not pick up the key of the student notebook."""

    key = traitlets.Unicode("").tag(sync=True)
    store = traitlets.Unicode("bpm-course-key").tag(sync=True)
    placeholder = traitlets.Unicode("Paste your key here").tag(sync=True)
    _esm = """
    export default {
      render({ model, el }) {
        const STORE = model.get("store");
        const row = document.createElement("div");
        row.style.cssText = "display:flex;gap:8px;align-items:center;flex-wrap:wrap";
        const input = document.createElement("input");
        input.type = "password";
        input.autocomplete = "off";
        input.placeholder = model.get("placeholder");
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


# --- the project's files ------------------------------------------------------------------------------------------------------

_locate = None


def use_project_files(locate) -> None:
    """Tell the kit how to find the project's files: `locate("data/bpi2017.parquet")` returns a path. A notebook on a hosted
    platform, where only the notebook file is delivered, passes the function that downloads them."""
    global _locate
    _locate = locate


def project_path(name: str) -> Path:
    return Path(_locate(name)) if _locate else Path(__file__).resolve().parent / name


def settings_figure(mo, name: str, width: int = 880):
    """One of the figures of the tutorial (img/settings-*.png): a setting of the explorer, boxed, above the maps it produces."""
    return mo.image(src=project_path(f"img/{name}").read_bytes(), width=width, rounded=True, alt=name.removesuffix(".png"))


# --- the steps of the analysis ------------------------------------------------------------------------------------------------
# Each is a plain function. A notebook runs it through record(), which stores its inputs and outputs as one step.


def load_event_log(name: str) -> pd.DataFrame:
    """One of the course logs. `name` is its place in the project, such as `data/bpi2017.parquet`: it is what gets recorded,
    so a recorded analysis names the file, not a folder of somebody's computer."""
    return pd.read_parquet(project_path(name))


def summarise_log(log: pd.DataFrame) -> dict:
    return {
        "cases": int(log[CASE_ID].nunique()),
        "events": len(log),
        "activities": int(log[ACTIVITY].nunique()),
        "columns": log.shape[1],
    }


def family_of(activity: str) -> str:
    """Application (A_), Offer (O_) or Workflow (W_), by the start of the activity name."""
    return _FAMILIES.get(activity[:2], "")


def activity_overview(log: pd.DataFrame) -> pd.DataFrame:
    """Every activity with its family (when the log has families), how many events it has and in how many cases it occurs."""
    grouped = log.groupby(ACTIVITY)
    table = pd.DataFrame({"events": grouped.size(), "cases": grouped[CASE_ID].nunique()})
    table["% of cases"] = (table["cases"] / log[CASE_ID].nunique() * 100).round(1)
    table = table.rename_axis("activity").reset_index()
    families = [family_of(name) for name in table["activity"]]
    if any(families):
        table.insert(1, "family", families)
        order = {name: i for i, name in enumerate(_FAMILIES.values())}
        table = table.assign(_order=table["family"].map(order)).sort_values(["_order", "events"], ascending=[True, False])
        table = table.drop(columns="_order")
    else:
        table = table.sort_values("events", ascending=False)
    return table.reset_index(drop=True)


def distinct_activities(log: pd.DataFrame) -> list:
    return sorted(log[ACTIVITY].unique())


# --- maps -----------------------------------------------------------------------------------------------------------------------
# A map is drawn from the settings below. They are the same in all three notebooks, and every recorded map keeps the settings
# that drew it (in its metadata), so a map seen in a replay can be opened again in the map explorer.

MAP_TYPES = {"Set-based": "set_based", "Last-activity-based": "last_activity_based", "Sequence-based": "sequence_based"}

# What a path in the map stands for. "application" uses the log's case id; "offer" regroups the events that carry an OfferID
# into one path per offer (a sub-log; O_Create Offer has no OfferID, so it is not part of an offer's path).
CASE_NOTIONS = {"A loan application": "application", "An offer (by OfferID)": "offer"}
_CASE_COLUMN = {"application": CASE_ID, "offer": "OfferID"}

DEFAULT_SETTINGS = {
    "activities": None,  # None draws every activity
    "map_type": "set_based",
    "allow_loops": True,
    "show_empty": True,
    "folds": {},
    "case_notion": "application",
}


def case_notions_of(log: pd.DataFrame) -> dict:
    """The case notions a log supports: the offer notion only when the log has an OfferID column."""
    return {label: key for label, key in CASE_NOTIONS.items() if _CASE_COLUMN[key] in log.columns}


def normalise_settings(settings: dict | None) -> dict:
    merged = {**DEFAULT_SETTINGS, **(settings or {})}
    merged["folds"] = {name: list(members) for name, members in (merged.get("folds") or {}).items()}
    if merged["activities"] is not None:
        merged["activities"] = list(merged["activities"])
    return merged


_services: dict = {}


def _service(log: pd.DataFrame, case_notion: str):
    """The map service for `log` under one case notion. Building it reads the whole log, so it is kept for the next map."""
    key = (id(log), len(log), case_notion)
    if key not in _services:
        column = _CASE_COLUMN[case_notion]
        events = log[log[column].notna()] if column != CASE_ID else log
        events = events[[column, ACTIVITY, TIMESTAMP]].rename(columns={column: CASE_ID})
        _services[key] = (lcm.get_service(events), set(events[ACTIVITY].unique()), int(events[CASE_ID].nunique()))
    return _services[key]


def draw_map(log, activities, map_type, allow_loops, show_empty, folds, case_notion, height=620):
    """A Linear Continuous Process Mapper map of `log`.

    `activities` are activity names as they are in the log (None for all). `folds` maps a fold name to the activities it
    replaces; a fold is drawn when at least one of its activities is selected. Selected activities that do not occur under the
    case notion are left out and listed in the metadata. Returns the Plotly figure and a dict that describes the map, including
    the settings that drew it.
    """
    service, available, cases = _service(log, case_notion)
    selected = sorted(available) if activities is None else list(activities)
    kept = [a for a in selected if a in available]
    left_out = [a for a in selected if a not in available]

    folds_used, fold_of = {}, {}
    for name, members in (folds or {}).items():
        name = (name or "").strip()
        present = [m for m in members if m in available]
        if name and present:
            folds_used[name] = present
            fold_of.update({m: name for m in present})
    drawn = list(dict.fromkeys(fold_of.get(a, a) for a in kept))
    if not drawn:
        raise ValueError("None of the selected activities occurs in this log under this case notion. Select other activities.")

    figure, metadata = service.generate(
        activities=drawn,
        map_type=map_type,
        allow_loops=allow_loops,
        visualize_empty_cases=show_empty,
        folds=folds_used,
    )
    figure.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10))
    settings = {
        "activities": None if activities is None else list(activities),
        "map_type": map_type,
        "allow_loops": allow_loops,
        "show_empty": show_empty,
        "folds": {k: list(v) for k, v in (folds or {}).items()},
        "case_notion": case_notion,
    }
    return figure, {**metadata, "cases": cases, "drawn": drawn, "left_out": left_out, "settings": settings}


def draw(log, settings, height=620):
    """`draw_map` from a settings dict (the map explorer's value)."""
    s = normalise_settings(settings)
    return draw_map(log, s["activities"], s["map_type"], s["allow_loops"], s["show_empty"], s["folds"], s["case_notion"], height)


def describe_settings(settings: dict) -> str:
    """The settings of a map in one Markdown paragraph."""
    s = normalise_settings(settings)
    abstraction = {v: k for k, v in MAP_TYPES.items()}[s["map_type"]]
    notion = {v: k for k, v in CASE_NOTIONS.items()}[s["case_notion"]]
    notion = notion[0].lower() + notion[1:]
    activities = "all activities" if s["activities"] is None else ", ".join(f"`{a}`" for a in s["activities"])
    folds = "; ".join(f"**{n}** = {', '.join(f'`{m}`' for m in ms)}" for n, ms in s["folds"].items()) or "none"
    return (
        f"**Abstraction:** {abstraction} · "
        + (f"**Each path is:** {notion} · " if s["case_notion"] != "application" else "")
        + f"**Self-loops:** {'shown' if s['allow_loops'] else 'hidden'} · **Empty traces:** {'shown' if s['show_empty'] else 'hidden'}  \n"
        f"**Activities:** {activities}  \n**Folds:** {folds}"
    )


def describe_map(meta) -> str:
    """The counts of a drawn map in one line."""
    if isinstance(meta, NotStored) or not isinstance(meta, dict):
        return ""
    return (
        f"{meta.get('cases', 0):,} paths · {meta['total_nodes']} nodes · {meta['nodes_leakage_gt_0']} nodes where paths end · "
        f"{meta['empty_cases']:,} empty traces"
    )


# --- the map explorer ---------------------------------------------------------------------------------------------------------
# The controls are one mo.ui.dictionary so that a notebook needs a single global name for them. A notebook keeps two marimo
# states: the *draft* settings the controls are built from (changed by the quick-selection buttons and by "open in the
# explorer") and the *drawn* settings (changed only by the Refresh button).

FOLD_SLOTS = 3


def activity_presets(names: list) -> dict:
    """Quick selections for the activity picker: one per family present in the log, all, and none."""
    presets = {}
    for prefix, family in _FAMILIES.items():
        members = [a for a in names if a.startswith(prefix)]
        if members:
            presets[f"{family} ({prefix})"] = members
    presets["All"] = list(names)
    presets["None"] = []
    return presets


def map_controls(mo, names: list, settings: dict | None, case_notions: dict):
    s = normalise_settings(settings)
    folds = list(s["folds"].items())[:FOLD_SLOTS]
    folds += [("", [])] * (FOLD_SLOTS - len(folds))
    notion_label = {v: k for k, v in case_notions.items()}.get(s["case_notion"], next(iter(case_notions)))
    return mo.ui.dictionary(
        {
            "activities": mo.ui.multiselect(
                options=names,
                value=[a for a in (names if s["activities"] is None else s["activities"]) if a in names],
                label="Activities to draw",
                full_width=True,
            ),
            "map_type": mo.ui.dropdown(
                options=MAP_TYPES, value={v: k for k, v in MAP_TYPES.items()}[s["map_type"]], label="Abstraction"
            ),
            "case_notion": mo.ui.dropdown(options=case_notions, value=notion_label, label="Each path is"),
            "allow_loops": mo.ui.switch(value=s["allow_loops"], label="Show self-loops"),
            "show_empty": mo.ui.switch(value=s["show_empty"], label="Show empty traces"),
            "folds": mo.ui.array(
                [
                    mo.ui.dictionary(
                        {
                            "name": mo.ui.text(value=name, placeholder="Fold name", label=f"Fold {i + 1}"),
                            "activities": mo.ui.multiselect(options=names, value=[m for m in members if m in names], label="replaces"),
                        }
                    )
                    for i, (name, members) in enumerate(folds)
                ]
            ),
        }
    )


def settings_from(value: dict, names: list) -> dict:
    """The settings that the controls' value describes."""
    activities = list(value["activities"])
    folds = {}
    for slot in value["folds"]:
        name = (slot["name"] or "").strip()
        if name and slot["activities"]:
            folds[name] = list(slot["activities"])
    return normalise_settings(
        {
            "activities": None if set(activities) == set(names) else sorted(activities),
            "map_type": value["map_type"],
            "allow_loops": value["allow_loops"],
            "show_empty": value["show_empty"],
            "folds": folds,
            "case_notion": value["case_notion"],
        }
    )


def fold_problems(settings: dict) -> list:
    """What is wrong with the folds, in words (an empty list when nothing is)."""
    problems, seen = [], {}
    for name, members in normalise_settings(settings)["folds"].items():
        for member in members:
            if member in seen:
                problems.append(f"`{member}` is in two folds ({seen[member]} and {name}). An activity can be in one fold only.")
            seen[member] = name
    return problems


def controls_layout(mo, controls, preset_buttons, refresh_button, status, show_case_notion: bool):
    first_row = [controls["map_type"]] + ([controls["case_notion"]] if show_case_notion else [])
    first_row += [controls["allow_loops"], controls["show_empty"]]
    folds = mo.vstack(
        [mo.hstack([slot["name"], slot["activities"]], justify="start", gap=1, widths=[1, 3]) for slot in controls["folds"]],
        gap=0.5,
    )
    return mo.vstack(
        [
            mo.hstack(first_row, justify="start", gap=2, align="end", wrap=True),
            mo.hstack([mo.md("Quick selection:"), preset_buttons], justify="start", gap=1, align="center"),
            controls["activities"],
            mo.accordion({"Activity folding": folds}),
            mo.hstack([refresh_button, status], justify="start", gap=1, align="center"),
        ],
        gap=0.75,
    )


def refresh_status(mo, current: dict, drawn: dict | None):
    if drawn is not None and current == drawn:
        return mo.md('<span style="color:#15803d">&#10003; The map shows these settings</span>')
    return mo.md('<span style="color:#b45309">&#9679; Settings changed: press Refresh visualization</span>')


# --- recording ----------------------------------------------------------------------------------------------------------------
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
        """The recorded state that produced `target`: what an annotation about it is attached to."""
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


# --- opening a recorded analysis ----------------------------------------------------------------------------------------------


def fetch_recorded(zip_name: str, sync_url: str | None, key: str | None):
    """A fresh folder with a recorded analysis, and where it came from.

    The course server is asked first (with a read key whose course is closed, so the analysis cannot be overwritten). When there is
    no server, no key or no answer, the copy kept in the repository (`zip_name`) is used.
    """
    from provenance_widget.portable import unpack_provenance
    from provenance_widget.sync import Sync

    folder = Path(tempfile.mkdtemp(prefix="bpm-recorded-")) / "provenance"
    if sync_url and key:
        try:
            if Sync(sync_url, key, folder).restore() == "restored":
                return folder, "the course server"
        except Exception:
            pass
    unpack_provenance(project_path(zip_name).read_bytes(), folder)
    return folder, "the copy in the course repository"


def open_recorded_analysis(zip_name: str, sync_url: str | None, key: str | None, history_name: str):
    """A tracker that reads the recorded analysis `history_name`, and where it came from (None, reason when it is not found).

    The course server is tried first; when it does not have the analysis, the copy in the repository is used."""
    tried = []
    for use_server in ([True] if sync_url and key else []) + [False]:
        try:
            folder, source = fetch_recorded(zip_name, sync_url if use_server else None, key if use_server else None)
            rt = open_recorded(folder, history_name)
            if rt is not None:
                return rt, source
            tried.append(f"{source} has no analysis named '{history_name}'")
        except Exception as problem:  # no network, no file: try the next place
            tried.append(str(problem))
    return None, "; ".join(tried)


def open_recorded(folder: Path, history_name: str):
    """A pmprov tracker that reads the history `history_name` in `folder` and records nothing. None when it is not there."""
    from provenance_widget.portable import relocate_artifacts
    from tracker.runtime import RuntimeTracker
    from tracker.storage import DuckDBSQLiteBackend

    (folder / "artifacts").mkdir(parents=True, exist_ok=True)
    relocate_artifacts(folder / "provenance.db", folder / "artifacts")
    storage = DuckDBSQLiteBackend(db_path=folder / "provenance.db", artifact_dir=folder / "artifacts")
    history = storage.find_latest_history_by_name(history_name)
    return None if history is None else RuntimeTracker.resume(storage, history, session_id="reviewer")
