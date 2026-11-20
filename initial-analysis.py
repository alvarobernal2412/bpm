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
    # Initial Event Log Analysis

    This notebook integrates a set of patterns for initial event log analysis that are useful for exploring the raw event log data before doing any specific process mining analysis such as behavioral, conformance, performance, or deviance analysis.
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
    import warnings as _warnings
    from pathlib import Path

    from tracker import init_marimo
    from provenance_widget.pmprov_adapter import PmprovAdapter
    from provenance_widget.widget import ProvenancePanel
    from provenance_widget.display import show_table
    from provenance_widget.portable import relocate_artifacts
    from provenance_widget.repeats import describe_run
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
        delivers only the notebook file). The log is downloaded once, the small files each time, so they are current."""
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
    import altair as alt
    import display_util as du
    import initial_analysis_kit as ak
    import temporal_characteristics_util as tcu

    alt.data_transformers.enable("vegafusion")

    # The course server that keeps each student's work. Set PMPROV_SYNC_URL to another address, or to an empty value to work
    # without a server (the work then stays in ./provenance next to the notebook).
    SYNC_URL = ak.course_server(_os.environ.get("PMPROV_SYNC_URL", "https://provenance.alvispace.com"))
    # (a student who said no to sharing has no server here, however the notebook was started: see ak.course_server)

    # pmprov warns that its cell rewriting is not active; the steps are recorded explicitly with record() below
    _warnings.filterwarnings("ignore", message=r"init_marimo\(\) was called but patch_marimo_ast_compile")
    return (
        HERE,
        Path,
        PmprovAdapter,
        ProvenancePanel,
        SYNC_URL,
        Sync,
        ak,
        describe_run,
        du,
        init_marimo,
        kit,
        mo,
        pd,
        project_file,
        relocate_artifacts,
        show_table,
        tcu,
    )


@app.cell(hide_code=True)
def _(SYNC_URL, kit, mo):
    key_box = mo.ui.anywidget(kit.KeyBox()) if SYNC_URL else None
    mo.vstack([mo.md("### Your key"), key_box]) if key_box is not None else mo.md("")
    return (key_box,)


@app.cell(hide_code=True)
def _(HERE, Path, SYNC_URL, Sync, ak, key_box, kit, mo):
    # With a server, nothing starts until there is a key; then the student's earlier work is brought back before anything opens
    # the provenance database.
    sync = None
    if SYNC_URL:
        _key = (key_box.value.get("key") or "").strip()
        mo.stop(not _key, mo.callout(mo.md("Enter your key above to start."), kind="info"))
        PROVENANCE_DIR = ak.session_folder(_key, ak.INITIAL_ANALYSIS_NOTEBOOK)
        sync = Sync(ak.sync_url(SYNC_URL, ak.INITIAL_ANALYSIS_NOTEBOOK), _key, PROVENANCE_DIR)
        sync.restore()
        mo.stop(sync.status.state == "unauthorized", mo.callout(mo.md(sync.status.message), kind="danger"))
    else:
        PROVENANCE_DIR = Path(kit.os.environ.get("PMPROV_DIR") or HERE / "provenance")
    (PROVENANCE_DIR / "artifacts").mkdir(parents=True, exist_ok=True)
    # which notebook this is, and a hash of its file: saved with the work, so the course server knows what version made it
    _info_file = ak.write_notebook_info(PROVENANCE_DIR, ak.INITIAL_ANALYSIS_NOTEBOOK, globals().get("__file__"))  # kept, so it is not shown
    return PROVENANCE_DIR, sync


@app.cell(hide_code=True)
def _(PROVENANCE_DIR, ak, init_marimo, kit, relocate_artifacts):
    # a history that was downloaded from another machine points at that machine's folders
    relocate_artifacts(PROVENANCE_DIR / "provenance.db", PROVENANCE_DIR / "artifacts")
    rt = init_marimo(
        history_name=ak.HISTORY_NAME,
        branch_name="main",
        db_path=str(PROVENANCE_DIR / "provenance.db"),
        artifact_dir=str(PROVENANCE_DIR / "artifacts"),
        fresh=False,  # continue the stored history of this name after a restart
    )
    return (rt,)


@app.cell(hide_code=True)
def _(PmprovAdapter, ProvenancePanel, rt):
    adapter = PmprovAdapter(rt)
    # the student can annotate, edit and export; there is no other mode in this notebook
    panel = ProvenancePanel(
        source=adapter,
        mode="analyst",
        tabs=["curated"],
        capture_charts=True,  # marimo's Visualize on every table, and the charts built there recorded
        empty_hint=(
            "No annotations yet. Press Anchor, click the table (or a cell of it, or a chart you built with Visualize) the annotation is about, write it with tags "
            "(for example intent or finding) and press Add."
        ),
    )
    return adapter, panel


@app.cell(hide_code=True)
def _(mo, panel):
    # mo.sidebar(...) has to be the last bare expression of its cell to render
    mo.sidebar(panel.sidebar())
    return


@app.cell(hide_code=True)
def _(mo, rt, sync):
    # saving starts once the history is open, and goes on a few seconds after every change
    if sync is not None:
        sync.settle = lambda: rt.storage._executor.submit(lambda: None).result()
        sync.start()
    save_tick = mo.ui.refresh(default_interval="5s", label="")
    return (save_tick,)


@app.cell(hide_code=True)
def _(mo, save_tick, sync):
    save_tick  # runs again every few seconds
    _parts = []
    if sync is not None:
        _kind = {"saved": "success", "idle": "neutral", "pending": "info"}.get(sync.status.state, "warn")
        _parts.append(mo.callout(mo.md(sync.status.message), kind=_kind))
    mo.vstack(_parts + [save_tick.style(display="none")])  # the timer has to be on the page to tick, but it is not a control
    return


@app.cell(hide_code=True)
def _(adapter, ak, rt):
    # Every step of the analysis goes through record(...): it runs the step and stores it, so that an annotation can be attached to the
    # table or map that the step produced, and the analysis can be replayed step by step.
    record, state_of = ak.analyst_recorder(rt, adapter)
    return record, state_of


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Event Log
    """)
    return


@app.cell(hide_code=True)
def _(ak, mo, project_file, record):
    # Load the event log; the step records the name of the file, not a folder of somebody's computer
    def load_event_log(name):
        return ak.load_event_log(project_file(name))

    event_log_from_disk = record(["event_log_from_disk"], load_event_log, ak.DHANA)
    mo.md(f"**{len(event_log_from_disk):,}** events loaded.")
    return (event_log_from_disk,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Log Initialization

    Initialize the event log with mandatory columns, time zone and -granularity.
    """)
    return


@app.cell(hide_code=True)
def _(ak, du, event_log_from_disk, mo, record, show_table, state_of):
    # Show the format used for each timestamp column of the event log loaded from disk
    timestamp_format_summary = record(["timestamp_format_summary"], ak.timestamp_formats, event_log_from_disk)

    timestamp_analyzer1 = mo.vstack([
        mo.md("Showing the format of each timestamp column in the initial event log loaded from disk, if unambiguously detected from the data recorded therein:"),
        show_table(
            du.table(timestamp_format_summary),
            artifact_id=state_of("timestamp_format_summary"), artifact_name="timestamp_formats",
        ),
    ])
    return (timestamp_analyzer1,)


@app.cell(hide_code=True)
def _(event_log_from_disk, mo, pd):
    # Select a timestamp attribute of the event log to inspect
    timestamp_columns = [col for col in event_log_from_disk.columns if isinstance(event_log_from_disk[col].dtype, pd.DatetimeTZDtype) or pd.api.types.is_datetime64_dtype(event_log_from_disk[col])]
    _timestamp_attributes = timestamp_columns

    timestamp_attribute_dropdown = mo.ui.dropdown(
        options=_timestamp_attributes,
        value=_timestamp_attributes[0] if _timestamp_attributes else None,
        label="Select a Timestamp attribute to inspect: ",
        searchable=True,
    )
    return timestamp_attribute_dropdown, timestamp_columns


@app.cell(hide_code=True)
def _(
    ak, du, event_log_from_disk, mo, record, show_table, state_of, timestamp_attribute_dropdown,
):
    # Show the granularity level of the encoded timestamps in the log, including whether timestamp components and timezone are constant
    timestamp_component_summary, timestamp_constant_prefixes = record(
        ["timestamp_component_summary", "timestamp_constant_prefixes"], ak.timestamp_components, event_log_from_disk
    )
    _selected_timestamp = timestamp_attribute_dropdown.value
    _component_view, _prefix_view = record(
        ["timestamp_component_view", "timestamp_prefix_view"],
        ak.select_timestamp_component, timestamp_component_summary, timestamp_constant_prefixes, _selected_timestamp,
    )

    granularity_analyzer = mo.vstack([
        mo.md(
            f"Showing the precision of '{_selected_timestamp}' and whether any timestamp "
            "elements are constant, based on the data recorded therein:"
        ),
        timestamp_attribute_dropdown,
        mo.ui.tabs({
            "Component analysis": show_table(
                du.table(_component_view), artifact_id=state_of("timestamp_component_view"), artifact_name="timestamp_components"
            ),
            "Constant prefixes": show_table(
                du.table(_prefix_view), artifact_id=state_of("timestamp_prefix_view"), artifact_name="timestamp_constant_prefixes"
            ),
        }),
    ])
    return (granularity_analyzer,)


@app.cell(hide_code=True)
def _(adapter, ak, fully_filled_columns, mo, timestamp_columns):
    import pytz

    _common_timezones = pytz.common_timezones
    # the widgets come back as the analyst left them when the page is opened again
    _resumed = ak.params_at(adapter, None, "initialize_log") or {}

    _default_timezone = _resumed.get("timezone") or ("UTC" if "UTC" in _common_timezones else _common_timezones[0])

    GRANULARITY_LEVELS = ['year', 'month', 'day', 'hour', 'minute', 'second', 'millisecond', 'sub-millisecond']

    # Define mandatory columns to be user selected from all consistent columns
    DEFAULT_CASE_ID = _resumed.get("case_id") or ak.CASE_ID
    DEFAULT_ACTIVITY = (ak.params_at(adapter, None, "classify_attributes") or {}).get("activity") or ak.ACTIVITY
    DEFAULT_COMPLETION_TIME = _resumed.get("completion_time") or ak.TIMESTAMP

    timezone_dropdown = mo.ui.dropdown(
        options=_common_timezones,
        value=_default_timezone,
        label="Select Time Zone",
        allow_select_none=False,
        searchable=True,
    )

    granularity_normalization_dropdown = mo.ui.dropdown(
        options=GRANULARITY_LEVELS,
        value=_resumed.get("granularity"),
        label="Select granularity level",
        allow_select_none=True,
    )

    CASE_ID_dropdown = mo.ui.dropdown(
        options=fully_filled_columns,
        value=DEFAULT_CASE_ID if DEFAULT_CASE_ID in fully_filled_columns else fully_filled_columns[0],
        label="CASE ID column",
        allow_select_none=False,
        searchable=True,
    )

    _timestamp_columns = [c for c in fully_filled_columns if c in set(timestamp_columns)]
    COMPLETION_TIME_dropdown = mo.ui.dropdown(
        options=_timestamp_columns,
        value=DEFAULT_COMPLETION_TIME if DEFAULT_COMPLETION_TIME in _timestamp_columns else _timestamp_columns[0],
        label="COMPLETION TIME column",
        allow_select_none=False,
        searchable=True,
    )

    ACTIVITY_dropdown = mo.ui.dropdown(
        options=fully_filled_columns,
        value=DEFAULT_ACTIVITY if DEFAULT_ACTIVITY in fully_filled_columns else fully_filled_columns[2],
        label="ACTIVITY column",
        allow_select_none=False,
        searchable=True,
    )

    return (
        ACTIVITY_dropdown,
        CASE_ID_dropdown,
        COMPLETION_TIME_dropdown,
        granularity_normalization_dropdown,
        timezone_dropdown,
    )


@app.cell(hide_code=True)
def _(
    ACTIVITY_dropdown,
    CASE_ID_dropdown,
    COMPLETION_TIME_dropdown,
    checkbox,
    granularity_normalization_dropdown,
    mo,
    timezone_dropdown,
):
    # the layout is its own cell: the checkbox changing must not rebuild (and so reset) the dropdowns
    log_initialization = mo.vstack([
        mo.md("Select a time zone to apply to all timestamp columns in the event log and case log:"),
        mo.hstack([timezone_dropdown], justify="start"),
        mo.md("(Optional) Select a granularity level to apply to all timestamp columns in the event log and case log:"),
        mo.hstack([granularity_normalization_dropdown], justify="start"),
        checkbox,
        mo.md("Select mandatory attributes from attributes that are fully filled:"),
        mo.hstack([CASE_ID_dropdown, COMPLETION_TIME_dropdown, ACTIVITY_dropdown])
    ])
    return (log_initialization,)


@app.cell(hide_code=True)
def _(
    CASE_ID,
    COMPLETION_TIME,
    ak,
    case_window_slider,
    checkbox,
    du,
    event_log_from_disk,
    granularity_normalization_dropdown,
    mo,
    record,
    show_table,
    state_of,
    timezone_dropdown,
):
    # Log Initialization: time zone, granularity, time frame, constant and empty columns, duplicates, ordering, folding.
    # The step records the choices made above as its arguments.
    initialized_event_log, initialization_messages, duplicate_event_instances = record(
        ["initialized_event_log", "initialization_messages", "duplicate_event_instances"],
        ak.initialize_log,
        event_log_from_disk,
        timezone_dropdown.value,
        granularity_normalization_dropdown.value,
        bool(checkbox.value),
        list(case_window_slider.value),  # a list: pmprov stores a tuple as text
        CASE_ID,
        COMPLETION_TIME,
    )

    _output = [mo.md("\n".join(f"- {_message}" for _message in initialization_messages))]
    if not duplicate_event_instances.empty:
        _output.append(mo.md("The following events had duplicates that have been removed, retaining only one:"))
        _output.append(
            show_table(
                du.table(duplicate_event_instances),
                artifact_id=state_of("duplicate_event_instances"), artifact_name="duplicate_events",
            )
        )

    initialization_summary = mo.vstack([mo.md("### Summary of the Initialization"), *_output])
    return initialization_summary, initialized_event_log


@app.cell(hide_code=True)
def _(CASE_ID, COMPLETION_TIME, ak, event_log_from_disk, mo, record, adapter):
    # Select a time frame; only cases that start and end within it are included in the event log
    DEFAULT_CASE_COUNT = 1500

    time_frame = record(["time_frame"], ak.time_frame, event_log_from_disk, CASE_ID, COMPLETION_TIME, DEFAULT_CASE_COUNT)

    CASE_WINDOW_UNIT = time_frame["unit"]
    _resumed = (ak.params_at(adapter, None, "initialize_log") or {}).get("window")
    _value = [0, time_frame["default"]]
    if _resumed:
        _value = [min(int(_resumed[0]), time_frame["stop"]), min(int(_resumed[1]), time_frame["stop"])]

    case_window_slider = mo.ui.range_slider(
        start=0,
        stop=time_frame["stop"],
        step=1,
        value=_value,
        label=f"Time frame in {'days' if CASE_WINDOW_UNIT == 'D' else 'hours'} after {time_frame['start']}",
        full_width=True,
        debounce=True,
    )

    time_frame_selector = mo.vstack([
        mo.md("Select a time frame. Only cases that are fully contained within it are "
            f"included for analysis. The initial selection covers the first {DEFAULT_CASE_COUNT} cases."
        ),
        case_window_slider
    ])
    return case_window_slider, time_frame_selector


@app.cell(hide_code=True)
def _(CASE_ID, COMPLETION_TIME, ak, du, initialized_event_log, mo, record, show_table, state_of):
    # Compute ordering information: are events ordered by completion time within each case and across the log?
    if initialized_event_log.empty:
        ordering_info = mo.md("_No case lies within the selected time frame._")
    else:
        case_ordering_summary, log_ordering_summary = record(
            ["case_ordering_summary", "log_ordering_summary"], ak.ordering_summaries, initialized_event_log, CASE_ID, COMPLETION_TIME
        )
        ordering_info = mo.hstack([
            show_table(du.table(case_ordering_summary), artifact_id=state_of("case_ordering_summary"), artifact_name="case_ordering"),
            show_table(du.table(log_ordering_summary), artifact_id=state_of("log_ordering_summary"), artifact_name="log_ordering"),
        ])
    return (ordering_info,)


@app.cell(hide_code=True)
def _(
    granularity_analyzer,
    initialization_summary,
    log_initialization,
    mo,
    ordering_info,
    time_frame_selector,
    timestamp_analyzer1,
):
    mo.ui.tabs({
        "Log Initialization" : log_initialization,
        "Initialization Summary" : initialization_summary,
        "Time Frame" : time_frame_selector,
        "Granularity Analysis" : granularity_analyzer,
        "Ordering Info": ordering_info,
        "Initial Timestamp attributes": timestamp_analyzer1
    })
    return


@app.cell(hide_code=True)
def _(initialized_event_log, mo):
    # an empty time frame has nothing to analyse: say so instead of failing in every cell below
    mo.stop(
        initialized_event_log.empty,
        mo.callout(mo.md("No case lies completely within the selected time frame. Widen the time frame."), kind="warn"),
    )
    event_log = initialized_event_log
    return (event_log,)


@app.cell(hide_code=True)
def _(adapter, ak, event_log_from_disk, mo):
    # identify columns that are filled for every row
    fully_filled_columns = [ col for col in event_log_from_disk.columns if event_log_from_disk[col].notna().all() ]

    _constant_columns = [ col for col in fully_filled_columns if event_log_from_disk[col].nunique() <= 1]
    fully_filled_columns = [ col for col in fully_filled_columns if col not in _constant_columns ]

    checkbox = mo.ui.checkbox(
        label="Enforce global ordering of the event log by completion time",
        value=bool((ak.params_at(adapter, None, "initialize_log") or {}).get("enforce_order", False)),
    )
    return checkbox, fully_filled_columns


@app.cell(hide_code=True)
def _(ACTIVITY_dropdown, CASE_ID_dropdown, COMPLETION_TIME_dropdown):
    # Name the mandatory attributes once. Everything downstream reads these rather than the dropdowns.
    CASE_ID = CASE_ID_dropdown.value
    ACTIVITY = ACTIVITY_dropdown.value
    COMPLETION_TIME = COMPLETION_TIME_dropdown.value
    return ACTIVITY, CASE_ID, COMPLETION_TIME


@app.cell(hide_code=True)
def _(ACTIVITY, CASE_ID, COMPLETION_TIME, ak, event_log, record):
    # Based on selected mandatory attributes, classify each attribute as mandatory, standard, or else
    attribute_classes = record(["attribute_classes"], ak.classify_attributes, event_log, CASE_ID, ACTIVITY, COMPLETION_TIME)

    MANDATORY_COLUMNS = attribute_classes["mandatory"]
    STANDARD_COLUMNS = attribute_classes["standard"]
    CASE_FEATURE_COLUMNS = attribute_classes["case_features"]
    activity_schema = attribute_classes["activity_schema"]
    activity_list = attribute_classes["activity_list"]
    activity_stats = attribute_classes["activity_stats"]
    return (
        CASE_FEATURE_COLUMNS,
        MANDATORY_COLUMNS,
        STANDARD_COLUMNS,
        activity_list,
        activity_stats,
        attribute_classes,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Events View

    The following tables extract different views from the event log. A _global_ attribute is available in each event. A _local_ attribute is available typically in one, sometimes in more than one activity schema. The _Case Inspection_ view is optimized for inspecting one or  more cases with event-specific data being folded into a single column. In the _Case Log_ view each row is a case of the log and only attributes that do never change in a case are shown. The _Raw Events_ view shows the raw, full event log for completeness only.

    Each view is equipped with Marimo-built features such as "_Visualize_" and "_Explore_".
    """)
    return


@app.cell(hide_code=True)
def _(adapter, ak, mo):
    _sample_enrichment = (
        "case_log['no_offers_per_case'] = event_log.groupby(CASE_ID)['OfferID'].nunique()\n"
        "case_log['max_offered_amount_per_case'] = event_log.groupby(CASE_ID)['OfferedAmount'].max()"
    )
    _resumed = (ak.params_at(adapter, None, "build_case_log") or {}).get("enrichment_code")

    # the code that was submitted last (what the case log is built with)
    get_enrichment_code, set_enrichment_code = mo.state(_resumed or "")
    applied_enrichment = {"code": _resumed or None}  # the code the case log was last built with successfully

    case_enrichment_code_editor = mo.ui.code_editor(
        value=_resumed or _sample_enrichment,
        language="python",
        label="Write your code here")
    return applied_enrichment, case_enrichment_code_editor, get_enrichment_code, set_enrichment_code


@app.cell(hide_code=True)
def _(case_enrichment_code_editor, mo, set_enrichment_code):
    _intro = mo.md(
        "### Manual Case Log Enrichment\n\n"
        "You can enrich the case log by hand, e.g., by aggregating values from the events grouped by case. "
        "Check how the case log has changed after clicking 'submit'."
    )

    case_enrichment_submit_button = mo.ui.button(
        label="Submit", on_click=lambda _: set_enrichment_code(case_enrichment_code_editor.value)
    )
    mo.vstack([_intro, case_enrichment_code_editor, case_enrichment_submit_button])
    return


@app.cell(hide_code=True)
def _(
    ACTIVITY,
    CASE_FEATURE_COLUMNS,
    CASE_ID,
    COMPLETION_TIME,
    ak,
    applied_enrichment,
    event_log,
    get_enrichment_code,
    mo,
    record,
):
    # Define case log; the enrichment code is an argument of the step, so the enrichment is part of the recorded analysis
    _code = get_enrichment_code() or None
    _error = None
    if _code:
        try:
            ak.build_case_log(event_log, CASE_ID, ACTIVITY, COMPLETION_TIME, CASE_FEATURE_COLUMNS, _code)
        except Exception as _problem:  # the student's code is theirs: show what went wrong, keep the earlier enrichment
            _error, _code = _problem, applied_enrichment["code"]
    applied_enrichment["code"] = _code

    if _error is None:
        case_log = record(
            ["case_log"], ak.build_case_log, event_log, CASE_ID, ACTIVITY, COMPLETION_TIME, CASE_FEATURE_COLUMNS, _code,
            name="build_case_log",
        )
    else:  # a failed submit is not a step: the case log stays as the last successful one made it
        case_log = ak.build_case_log(event_log, CASE_ID, ACTIVITY, COMPLETION_TIME, CASE_FEATURE_COLUMNS, _code)
    mo.callout(
        mo.md(f"The new enrichment code was not applied (the case log keeps the last working one): `{type(_error).__name__}: {_error}`"),
        kind="danger",
    ) if _error else None
    return (case_log,)


@app.cell(hide_code=True)
def _(activity_list, adapter, ak, mo):
    _resumed = ak.params_at(adapter, None, "local_attribute_view") or {}
    _chosen = [a for a in (_resumed.get("activities") or []) if a in activity_list]
    activity_multiselect = mo.ui.multiselect(
        options=activity_list,
        value=_chosen or (activity_list[:1] if len(activity_list) >= 1 else activity_list),
        label="Select activities to see local attributes",
    )
    hide_case_features_checkbox = mo.ui.checkbox(
        label="Hide attributes that are also case-level attributes", value=bool(_resumed.get("hide_case_features", False))
    )
    return activity_multiselect, hide_case_features_checkbox


@app.cell(hide_code=True)
def _(
    activity_multiselect,
    ak,
    attribute_classes,
    du,
    event_log,
    hide_case_features_checkbox,
    mo,
    record,
    show_table,
    state_of,
):
    _selected_activities = list(activity_multiselect.value)

    local_attribute_table = record(
        ["local_attribute_table"], ak.local_attribute_view,
        event_log, _selected_activities, attribute_classes, bool(hide_case_features_checkbox.value),
        name="local_attribute_view",
    )

    local_view = mo.vstack([
        mo.md("Select one or more activities to view only the data attributes that are common to their schemas:"),
        activity_multiselect,
        hide_case_features_checkbox,
        show_table(
            du.table(local_attribute_table, pagination=True, page_size=15),
            artifact_id=state_of("local_attribute_table"), artifact_name="local_attributes",
        )
        if _selected_activities
        else mo.md("_No activities selected._"),
    ])
    return (local_view,)


@app.cell(hide_code=True)
def _(ak, attribute_classes, case_log, du, event_log, local_view, mo, show_table, state_of):
    # du.table rather than the frames themselves: a timedelta column pushes marimo's chart builder off the Arrow path.
    _views = ak.event_views(event_log, attribute_classes)
    _log_step = state_of("initialized_event_log")
    mo.ui.tabs({
        "Global Attributes": show_table(du.table(_views["global"]), artifact_id=_log_step, artifact_name="global_attributes"),
        "Local Attributes": local_view,
        "Case Inspection": show_table(du.table(_views["inspection"]), artifact_id=_log_step, artifact_name="case_inspection"),
        "Case Log": show_table(du.table(case_log), artifact_id=state_of("case_log"), artifact_name="case_log"),
        "Raw Events": show_table(du.table(event_log), artifact_id=_log_step, artifact_name="raw_events"),
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Activity Schemas View

    A _schema_ of a given activity is the set of all attributes such that at least one event of the activity has a value for that attribute. Therefore, each _global_ attribute is in each schema. _Local_ attributes can be _shared_ between the schema of two or more activities or _exclusive_ to one activity schema.
    """)
    return


@app.cell(hide_code=True)
def _(
    ACTIVITY,
    CASE_ID,
    MANDATORY_COLUMNS,
    STANDARD_COLUMNS,
    activity_stats,
    ak,
    event_log,
    record,
):
    schema_usages, partial_schema_usages = record(
        ["schema_usages", "partial_schema_usages"],
        ak.schema_views, event_log, CASE_ID, ACTIVITY, MANDATORY_COLUMNS, STANDARD_COLUMNS, activity_stats,
    )
    return partial_schema_usages, schema_usages


@app.cell(hide_code=True)
def _(du, mo, partial_schema_usages, schema_usages, show_table, state_of):
    # Show schemas, schema population, and overlaps
    mo.ui.tabs({
        "Activity Schemas": show_table(
            du.table(schema_usages[['incidence', 'local_attributes', 'missing_values']]),
            artifact_id=state_of("schema_usages"), artifact_name="activity_schemas",
        ),
        "Schema Overlaps": show_table(
            du.table(partial_schema_usages[(partial_schema_usages != 0).any(axis=1)]),
            artifact_id=state_of("partial_schema_usages"), artifact_name="schema_overlaps",
        ),
    })
    return


if __name__ == "__main__":
    app.run()
