# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.2",
#     "pmprov[duckdb,parquet,graph]>=0.10.0",
#     "marimo-pmprov[pdf]>=0.13.0",
#     "pandas>=3.1.0",
#     "pyarrow>=15",
#     "altair>=5.5",
#     "vegafusion>=2.0",
#     "pytz",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Initial Event Log Analysis: a student's work
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
    import os as _os
    import shutil as _shutil
    import sys as _sys
    import tempfile as _tempfile
    import urllib.request as _request
    from pathlib import Path

    from provenance_widget.pmprov_adapter import PmprovAdapter
    from provenance_widget.widget import ProvenancePanel
    from provenance_widget.display import show_recorded_charts, show_table
    from provenance_widget.sync import Sync

    def _folder_of_this_notebook():
        try:
            folder = Path(str(mo.notebook_location()))
            if folder.is_dir():
                return folder
        except Exception:
            pass
        return Path.cwd()

    HERE = _folder_of_this_notebook()
    RAW_URL = "https://raw.githubusercontent.com/alvarobernal2412/bpm/main/"

    def project_file(relative, refresh=False):
        """A file of this project: next to the notebook in a local checkout, otherwise downloaded from the repository (molab
        delivers only the notebook file)."""
        local = HERE / relative
        if local.exists():
            return local
        cached = Path(_tempfile.gettempdir()) / "bpm-project-files" / relative
        if refresh or not cached.exists():
            cached.parent.mkdir(parents=True, exist_ok=True)
            part = cached.with_name(cached.name + ".part")
            with _request.urlopen(RAW_URL + relative, timeout=600) as response, open(part, "wb") as out:
                _shutil.copyfileobj(response, out)
            part.replace(cached)
        return cached

    _kit_file = project_file("bpm_kit.py", refresh=True)
    if str(_kit_file.parent) not in _sys.path:
        _sys.path.insert(0, str(_kit_file.parent))
    import bpm_kit as kit

    kit.use_project_files(project_file)

    # the helper modules of the analysis (the `lib/` folder of the repository), found next to the notebook or downloaded
    _lib = [project_file(f"lib/{name}.py", refresh=True) for name in (
        "temporal_characteristics_util", "data_quality_util", "display_util", "initial_analysis_kit")]
    if str(_lib[0].parent) not in _sys.path:
        _sys.path.insert(0, str(_lib[0].parent))
    import display_util as du
    import initial_analysis_kit as ak

    # The course server that keeps each student's work. A reviewer only reads it: nothing here ever saves.
    SYNC_URL = _os.environ.get("PMPROV_SYNC_URL", "https://provenance.alvispace.com")
    return PmprovAdapter, ProvenancePanel, Path, SYNC_URL, Sync, ak, du, kit, mo, pd, show_recorded_charts, show_table


@app.cell(hide_code=True)
def _(kit, mo):
    key_box = mo.ui.anywidget(
        kit.KeyBox(store="bpm-reviewer-key", placeholder="Paste the student's key here")
    )
    mo.vstack([mo.md("### The student's key"), key_box])
    return (key_box,)


@app.cell(hide_code=True)
def _(SYNC_URL, Path, Sync, ak, key_box, kit, mo):
    # The student's work is copied into a fresh folder and opened there, without a Sync that saves: a reviewer cannot change it.
    mo.stop(not SYNC_URL, mo.callout(mo.md("This notebook needs the course server (`PMPROV_SYNC_URL`)."), kind="danger"))
    _key = (key_box.value.get("key") or "").strip()
    mo.stop(not _key, mo.callout(mo.md("Paste the student's key above to start."), kind="info"))
    folder = Path(kit.tempfile.mkdtemp(prefix="bpm-review-")) / "provenance"
    _sync = Sync(ak.sync_url(SYNC_URL, ak.INITIAL_ANALYSIS_NOTEBOOK), _key, folder)
    _result = _sync.restore()
    mo.stop(
        _sync.status.state == "unauthorized",
        mo.callout(mo.md(_sync.status.message), kind="danger"),
    )
    mo.stop(
        _result == "failed",
        mo.callout(mo.md(f"The course server could not be reached: {_sync.status.message}"), kind="danger"),
    )
    mo.stop(
        _result == "empty",
        mo.callout(mo.md("Nothing is saved under this key yet: the student has not started."), kind="warn"),
    )
    rt = kit.open_recorded(folder, ak.HISTORY_NAME)
    mo.stop(
        rt is None,
        mo.callout(
            mo.md(f"The work saved under this key has no analysis named '{ak.HISTORY_NAME}'. Is it the key of the initial-analysis notebook?"),
            kind="danger",
        ),
    )
    return (rt,)


@app.cell(hide_code=True)
def _(PmprovAdapter, ProvenancePanel, mo, rt):
    adapter = PmprovAdapter(rt)
    panel = ProvenancePanel(source=adapter, mode="reviewer")
    panel.refresh()  # build the tree now, so the first snapshot below already knows its step
    get_cursor = panel.reactive_cursor(mo.state)  # moved by the arrows and by Replay
    return adapter, get_cursor, panel


@app.cell(hide_code=True)
def _(mo, panel):
    # mo.sidebar(...) has to be the last bare expression of its cell to render
    mo.sidebar(panel.sidebar())
    return


@app.cell(hide_code=True)
def _(adapter, get_cursor, kit, mo, panel):
    # Here record(...) runs nothing: it returns what a step produced at the step the side panel is on.
    cursor_state = get_cursor() or adapter.latest_state_id()
    snap = panel.snapshot(cursor_state)
    record, state_of = kit.reviewer_recorder(snap, mo)
    return cursor_state, record, snap, state_of


@app.cell(hide_code=True)
def _(adapter, cursor_state, mo, show_recorded_charts):
    # the charts the student built in a table's Visualize tab, up to the step the side panel is on (nothing when there are none)
    _charts = show_recorded_charts(adapter, cursor_state)
    mo.vstack([mo.md("## Charts built in Visualize"), _charts]) if _charts.text else mo.md("")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook replays the work a student did in `01_initial-analysis.py`. Step through the analysis with the arrows in the side panel:
    each table shows what it looked like at the step you are on, and a table whose step has not happened yet says so. The choices
    the student made (time zone, time frame, ...) are shown as text; nothing here can be changed, and nothing is saved.
    """)
    return


@app.cell(hide_code=True)
def _(adapter, ak, cursor_state, du, mo, project_file, show_table, snap, state_of):
    # The log the student worked on is loaded here: it is too large to travel with their work (values over 500 KB are left out of the
    # stored analysis). What was computed from it is rebuilt from the arguments the student's steps were recorded with.
    event_log_from_disk = ak.load_event_log(project_file(ak.DHANA))

    def params(step):
        """The arguments of the last `step` up to the step the side panel is on."""
        return ak.params_at(adapter, cursor_state, step) or {}

    def recorded(name, again=None):
        """`(value, None)`, or `(None, message)` when the step has not happened yet at the step the panel is on, or its result was left
        out of the stored analysis and cannot be rebuilt (`again` rebuilds it)."""
        status = snap.status(name)
        if status == "not_computed":
            return None, mo.md(snap.missing(name))
        value = snap.get(name) if status == "ok" else None
        if value is None and again is not None:
            value = again()
        if value is None:
            return None, mo.md("_This result was too large to be stored with the analysis._")
        return value, None

    _made: dict = {}

    def initialized(state=None):
        """The log as `initialize_log` made it, with the arguments recorded for that step (the last one up to `state`, by default up
        to the step the panel is on)."""
        key = state or cursor_state
        if key not in _made:
            p = ak.params_at(adapter, key, "initialize_log") or {}
            _made[key] = ak.initialize_log(
                event_log_from_disk, p["timezone"], p["granularity"], bool(p["enforce_order"]), p["window"], p["case_id"], p["completion_time"]
            )[0]
        return _made[key]

    def table_view(name, artifact_name, transform=None, anchor=None, again=None):
        """A recorded table, anchorable as the student's was (same artifact name, and the step that produced it)."""
        value, problem = recorded(name, again)
        if problem is not None:
            return problem
        frame = transform(value) if transform else value
        return show_table(du.table(frame), artifact_id=state_of(anchor or name), artifact_name=artifact_name)

    return event_log_from_disk, initialized, params, recorded, table_view


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Event Log
    """)
    return


@app.cell(hide_code=True)
def _(event_log_from_disk, mo):
    mo.md(f"**{len(event_log_from_disk):,}** events loaded.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Log Initialization
    """)
    return


@app.cell(hide_code=True)
def _(mo, params, recorded, snap):
    # the choices the student made, read from the arguments of the recorded steps at the step the panel is on
    _init = params("initialize_log") if snap.status("initialized_event_log") != "not_computed" else None
    _classes = params("classify_attributes")
    _frame, _ = recorded("time_frame")
    if _init is None:
        choices = mo.md("_The log has not been initialized at this step._")
    else:
        _window = _init.get("window") or [0, 0]
        _unit = "days" if (_frame or {}).get("unit") == "D" else "hours"
        _start = (_frame or {}).get("start")
        choices = mo.md("\n".join([
            f"- Time zone: **{_init.get('timezone')}**",
            f"- Granularity: **{_init.get('granularity') or 'not changed'}**",
            f"- Global ordering of the event log: **{'yes' if _init.get('enforce_order') else 'no'}**",
            f"- Time frame: **{_window[0]} to {_window[1]} {_unit}** after {_start}" if _start is not None
            else f"- Time frame: **{_window[0]} to {_window[1]}**",
            f"- Case ID: `{_init.get('case_id')}`, completion time: `{_init.get('completion_time')}`"
            + (f", activity: `{_classes.get('activity')}`" if _classes else ""),
        ]))
    return (choices,)


@app.cell(hide_code=True)
def _(mo, params, table_view):
    _column = params("select_timestamp_component").get("column")
    granularity_view = mo.vstack([
        mo.md(f"Precision of the timestamps of '{_column}' and whether any timestamp elements are constant:")
        if _column else mo.md(""),
        mo.ui.tabs({
            "Component analysis": table_view("timestamp_component_view", "timestamp_components"),
            "Constant prefixes": table_view("timestamp_prefix_view", "timestamp_constant_prefixes"),
        }),
    ])
    return (granularity_view,)


@app.cell(hide_code=True)
def _(choices, granularity_view, mo, recorded, table_view):
    _messages, _problem = recorded("initialization_messages")
    _dupes, _ = recorded("duplicate_event_instances")
    summary = mo.vstack([
        _problem if _problem is not None else mo.md("\n".join(f"- {m}" for m in _messages)),
        table_view("duplicate_event_instances", "duplicate_events")
        if _dupes is not None and len(_dupes) > 0
        else mo.md(""),
    ])
    mo.ui.tabs({
        "Log Initialization": choices,
        "Initialization Summary": summary,
        "Granularity Analysis": granularity_view,
        "Ordering Info": mo.hstack([
            table_view("case_ordering_summary", "case_ordering"),
            table_view("log_ordering_summary", "log_ordering"),
        ]),
        "Initial Timestamp attributes": table_view("timestamp_format_summary", "timestamp_formats"),
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Events View

    A _global_ attribute is available in each event, a _local_ attribute in one or some activity schemas. The _Case Inspection_
    view folds the event-specific data into a single column; in the _Case Log_ each row is a case.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # The student's enrichment code is theirs: it runs here only when the reviewer asks for it.
    run_enrichment = mo.ui.run_button(label="Run the student's enrichment code")
    return (run_enrichment,)


@app.cell(hide_code=True)
def _(adapter, ak, cursor_state, initialized, mo, params, recorded, run_enrichment, table_view):
    _classes, _no_classes = recorded("attribute_classes")

    def _view(which):
        return lambda log: ak.event_views(log, _classes)[which]

    def _case_log_again():
        # everything from the step that built the case log, not from later steps the panel may have passed
        state = ak.step_state_id(adapter, cursor_state, "build_case_log")
        p = ak.params_at(adapter, state, "build_case_log")
        code = p.get("enrichment_code") if run_enrichment.value else None
        return ak.build_case_log(initialized(state), p["case_id"], p["activity"], p["completion_time"], p["case_features"], code)

    def _local_again():
        state = ak.step_state_id(adapter, cursor_state, "local_attribute_view")
        p = ak.params_at(adapter, state, "local_attribute_view")
        return ak.local_attribute_view(initialized(state), p["activities"], p["found"], bool(p["hide_case_features"]))

    _local = params("local_attribute_view")
    _code = params("build_case_log").get("enrichment_code")
    _by_classes = lambda build: _no_classes if _classes is None else build()  # noqa: E731

    mo.ui.tabs({
        "Global Attributes": _by_classes(lambda: table_view(
            "initialized_event_log", "global_attributes", _view("global"), again=initialized)),
        "Local Attributes": mo.vstack([
            mo.md(
                f"Activities selected: {', '.join(f'`{a}`' for a in _local.get('activities', [])) or '_none_'}"
                + (" (attributes that are also case-level attributes hidden)" if _local.get("hide_case_features") else "")
            ) if _local else mo.md(""),
            table_view("local_attribute_table", "local_attributes", again=_local_again),
        ]),
        "Case Inspection": _by_classes(lambda: table_view(
            "initialized_event_log", "case_inspection", _view("inspection"), again=initialized)),
        "Case Log": mo.vstack([
            mo.md("The student enriched the case log with:") if _code else mo.md(""),
            mo.md(f"```python{chr(10)}{_code}{chr(10)}```") if _code else mo.md(""),
            mo.vstack([
                mo.callout(mo.md(
                    "If the case log below had to be rebuilt here, it is built **without** this code: it is the student's, and it runs in "
                    "your kernel only if you press the button."), kind="warn"),
                run_enrichment,
            ]) if _code else mo.md(""),
            table_view("case_log", "case_log", again=_case_log_again),
        ]),
        "Raw Events": table_view("initialized_event_log", "raw_events", again=initialized),
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Activity Schemas View

    A _schema_ of an activity is the set of all attributes that at least one event of the activity has a value for.
    """)
    return


@app.cell(hide_code=True)
def _(mo, table_view):
    mo.ui.tabs({
        "Activity Schemas": table_view(
            "schema_usages", "activity_schemas", lambda u: u[["incidence", "local_attributes", "missing_values"]]),
        "Schema Overlaps": table_view(
            "partial_schema_usages", "schema_overlaps", lambda p: p[(p != 0).any(axis=1)]),
    })
    return


if __name__ == "__main__":
    app.run()
