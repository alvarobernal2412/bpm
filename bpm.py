# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.2",
#     "pmprov[duckdb,parquet,graph]>=0.10.0",
#     "marimo-pmprov[pdf]>=0.4.2",
#     "linear-continuous-process-mapper>=0.1.0",
#     "plotly>=7.1.0",
#     "kaleido>=1.0.0",
#     "networkx>=3.7",
#     "pandas>=3.1.0",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Loan applications: what do we know about a new application?

    You will explore a real event log of a bank's loan approval process (BPI Challenge 2017: 31,509 applications, 1.2 million
    events) with process maps, and write down what you find.

    **How to use this notebook**

    1. Enter your key below. If you worked here before, your earlier work comes back by itself.
    2. Read each question, look at the table or the map, and answer in the side panel: press **Pick**, click the table or map
       you mean, write your note and press **Add**.
    3. Your work is saved automatically. You can close this page and come back with the same key.

    **The three questions**

    1. Which data (attributes) does the first activity, `A_Create Application`, carry?
    2. Which of those attributes are sometimes empty?
    3. Is any attribute used by more than one activity?

    A map shows the order of activities, not attributes. To use a map for an attribute question, we first keep only the
    events that carry that attribute: the activities in such a map are exactly the activities that carry it.
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
    import hashlib as _hashlib
    import os as _os
    import tempfile as _tempfile
    from pathlib import Path

    import anywidget
    import traitlets

    import warnings as _warnings

    from tracker import init_marimo
    from tracker.runtime import RuntimeTracker
    from tracker.storage import DuckDBSQLiteBackend
    from provenance_widget.pmprov_adapter import PmprovAdapter
    from provenance_widget.widget import ProvenancePanel
    from provenance_widget.display import show, show_chart, show_table
    from provenance_widget.portable import relocate_artifacts, unpack_provenance, zip_provenance
    from provenance_widget.repeats import describe_run
    from provenance_widget.sync import Sync

    def _folder_of_this_notebook():
        # mo.notebook_location() is the folder of the notebook; if a platform returns something else, use the
        # working directory, where the project's files are
        try:
            folder = Path(str(mo.notebook_location()))
            if folder.is_dir():
                return folder
        except Exception:
            pass
        return Path.cwd()

    HERE = _folder_of_this_notebook()

    PROJECT_ZIP_URL = "https://github.com/alvarobernal2412/bpm/archive/refs/heads/main.zip"

    def project_files(here):
        """The folder that holds `data/` (the log).

        Next to the notebook when the whole folder is there (a local checkout). A platform that delivers only the
        notebook file, such as molab opening it from GitHub, does not bring it, so it is downloaded once from
        the repository into a temporary folder.
        """
        if (here / "data" / "bpi2017.parquet").exists():
            return here
        target = Path(_tempfile.gettempdir()) / "bpm-project-files"
        if not (target / "data" / "bpi2017.parquet").exists():
            import io
            import urllib.request
            import zipfile

            with urllib.request.urlopen(PROJECT_ZIP_URL, timeout=300) as response:
                archive = zipfile.ZipFile(io.BytesIO(response.read()))
            for member in archive.namelist():
                parts = member.split("/", 1)  # "bpm-main/data/x" -> "data/x"
                if len(parts) == 2 and parts[1].startswith("data/") and not member.endswith("/"):
                    destination = target / parts[1]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(member))
        return target

    # The course server that keeps each student's work. Set PMPROV_SYNC_URL to another address, or to an empty value to
    # work without a server (the work then stays in ./provenance next to the notebook).
    SYNC_URL = _os.environ.get("PMPROV_SYNC_URL", "https://provenance.alvispace.com")

    def session_folder(key):
        """Where this student's work lives while the notebook runs: one folder per key, so students who share a hosted
        notebook never write into each other's provenance."""
        return Path(_tempfile.gettempdir()) / "bpm-provenance" / _hashlib.sha256(key.encode()).hexdigest()[:16]

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

    HISTORY_NAME = "BPI 2017 Task 1 with LCM maps"

    class NotStored:
        """Stands in for a value that was recorded but left out of the provenance zip to keep it small."""

        def __repr__(self):
            return "<not stored>"

    # pmprov warns that its cell rewriting is not active; the steps are recorded explicitly with record() below
    _warnings.filterwarnings("ignore", message=r"init_marimo\(\) was called but patch_marimo_ast_compile")

    return (
        DuckDBSQLiteBackend,
        HERE,
        HISTORY_NAME,
        KeyBox,
        NotStored,
        Path,
        PmprovAdapter,
        ProvenancePanel,
        RuntimeTracker,
        SYNC_URL,
        Sync,
        describe_run,
        init_marimo,
        mo,
        pd,
        project_files,
        relocate_artifacts,
        session_folder,
        show,
        show_chart,
        show_table,
        unpack_provenance,
        zip_provenance,
    )


@app.cell(hide_code=True)
def _(mo):
    # The mode is chosen before the run when it can be: `marimo run bpm.py -- --mode reviewer`, or the PMPROV_MODE
    # environment variable. A hosted notebook (molab) cannot be started with either, so then the notebook shows a switch.
    import os as _os

    MODE_GIVEN = mo.cli_args().get("mode") or _os.environ.get("PMPROV_MODE") or None
    if MODE_GIVEN not in (None, "analyst", "reviewer"):
        raise ValueError(f"mode must be 'analyst' or 'reviewer', not {MODE_GIVEN!r}")
    mode_switch = mo.ui.radio(
        options={"Work on the analysis": "analyst", "Look back through my work": "reviewer"},
        value="Work on the analysis",
        inline=True,
    )
    return MODE_GIVEN, mode_switch


@app.cell(hide_code=True)
def _(MODE_GIVEN, mo, mode_switch):
    mo.callout(
        mo.md(f"Mode: **{MODE_GIVEN}** (chosen before the run).")
        if MODE_GIVEN
        else mo.hstack([mode_switch, mo.md("You can switch at any time.")], justify="start", gap=2),
        kind="info",
    )
    return


@app.cell(hide_code=True)
def _(MODE_GIVEN, mode_switch):
    MODE = MODE_GIVEN or mode_switch.value
    return (MODE,)


@app.cell(hide_code=True)
def _(KeyBox, SYNC_URL, mo):
    key_box = mo.ui.anywidget(KeyBox()) if SYNC_URL else None
    mo.vstack([mo.md("### Your key"), key_box]) if key_box else mo.md("*Working without a server: your work stays in this notebook's folder.*")
    return (key_box,)


@app.cell(hide_code=True)
def _(HERE, Path, SYNC_URL, Sync, key_box, mo, session_folder):
    # With a server, nothing starts until there is a key; then the student's earlier work is brought back before
    # anything opens the provenance database.
    import os as _os

    sync = None
    if SYNC_URL:
        _key = (key_box.value.get("key") or "").strip()
        mo.stop(not _key, mo.callout(mo.md("Enter your key above to start."), kind="info"))
        PROVENANCE_DIR = session_folder(_key)
        sync = Sync(SYNC_URL, _key, PROVENANCE_DIR)
        sync.restore()
        mo.stop(sync.status.state == "unauthorized", mo.callout(mo.md(sync.status.message), kind="danger"))
    else:
        PROVENANCE_DIR = Path(_os.environ.get("PMPROV_DIR") or HERE / "provenance")
    (PROVENANCE_DIR / "artifacts").mkdir(parents=True, exist_ok=True)
    return PROVENANCE_DIR, sync


@app.cell(hide_code=True)
def _(MODE, mo):
    # A hosted notebook has its own files, so a reviewer gets the provenance as the zip file the analyst downloads.
    uploaded_provenance = mo.ui.file(filetypes=[".zip"], kind="area", label="Drop provenance.zip here")
    mo.vstack([
        mo.md(
            "**Provenance.** Download `provenance.zip` from an analyst session and drop it here (or put it next to this "
            "notebook). Dropping a file replaces the history that is loaded."
        ),
        uploaded_provenance,
    ]) if MODE == "reviewer" else None
    return (uploaded_provenance,)


@app.cell(hide_code=True)
def _(
    DuckDBSQLiteBackend,
    HERE,
    HISTORY_NAME,
    MODE,
    PROVENANCE_DIR,
    RuntimeTracker,
    init_marimo,
    mo,
    relocate_artifacts,
    unpack_provenance,
    uploaded_provenance,
):
    if MODE == "analyst":
        # a history that was downloaded from another machine points at that machine's folders
        relocate_artifacts(PROVENANCE_DIR / "provenance.db", PROVENANCE_DIR / "artifacts")
        rt = init_marimo(
            history_name=HISTORY_NAME,
            branch_name="main",
            db_path=str(PROVENANCE_DIR / "provenance.db"),
            artifact_dir=str(PROVENANCE_DIR / "artifacts"),
            fresh=False,  # continue the stored history of this name after a restart
        )
    else:
        # a zip dropped into the notebook, or a provenance.zip next to it, becomes the folder that is read
        if uploaded_provenance.value:
            unpack_provenance(uploaded_provenance.value[0].contents, PROVENANCE_DIR)
        elif not (PROVENANCE_DIR / "provenance.db").exists() and (HERE / "provenance.zip").exists():
            unpack_provenance((HERE / "provenance.zip").read_bytes(), PROVENANCE_DIR)

        mo.stop(
            not (PROVENANCE_DIR / "provenance.db").exists(),
            mo.callout(mo.md("No provenance loaded yet. Drop the `provenance.zip` of an analyst session above."), kind="warn"),
        )
        relocate_artifacts(PROVENANCE_DIR / "provenance.db", PROVENANCE_DIR / "artifacts")
        _storage = DuckDBSQLiteBackend(
            db_path=PROVENANCE_DIR / "provenance.db", artifact_dir=PROVENANCE_DIR / "artifacts"
        )
        _history_id = _storage.find_latest_history_by_name(HISTORY_NAME)
        mo.stop(
            _history_id is None,
            mo.callout(mo.md(f"The store has no history named `{HISTORY_NAME}`. Record one in analyst mode first."), kind="warn"),
        )
        # Resume the stored history without installing the kernel hooks of init_marimo(): a reviewer records nothing.
        rt = RuntimeTracker.resume(_storage, _history_id, session_id="reviewer")

    return (rt,)


@app.cell(hide_code=True)
def _(MODE, PROVENANCE_DIR, mo, rt, zip_provenance):
    mo.stop(MODE != "analyst")

    def provenance_zip():
        """The history as one small zip file: the steps and notes, and the values small enough to carry."""
        rt.storage._executor.submit(lambda: None).result()  # let the writes that are still queued land first
        data, _left_out = zip_provenance(PROVENANCE_DIR)
        return data

    mo.vstack([
        mo.md(
            "Your work is saved for you. If you also want a copy on your own computer, download it here "
            "(it keeps every step, note, table and map, and is small)."
        ),
        mo.download(data=provenance_zip, filename="provenance.zip", label="Download a copy of my work"),
    ])
    return


@app.cell(hide_code=True)
def _(MODE, PmprovAdapter, ProvenancePanel, mo, rt):
    adapter = PmprovAdapter(rt)
    if MODE == "analyst":
        # the analyst can annotate, edit and export
        panel = ProvenancePanel(source=adapter, mode="analyst", tabs=["curated"])
        get_cursor = None
    else:
        panel = ProvenancePanel(source=adapter, mode="reviewer")
        # build the tree now, not in the background, so the first snapshot below already knows its step
        panel.refresh()
        # every step of the stepper, and every Replay on a note, moves this cursor; cells that call get_cursor() re-run
        get_cursor = panel.reactive_cursor(mo.state)
    return adapter, get_cursor, panel


@app.cell(hide_code=True)
def _(mo, panel):
    # mo.sidebar(...) has to be the last bare expression of its cell to render
    mo.sidebar(panel.sidebar())
    return


@app.cell(hide_code=True)
def _(MODE, mo, rt, sync):
    # saving starts once the history is open, and goes on a few seconds after every change
    if sync is not None and MODE == "analyst":
        sync.settle = lambda: rt.storage._executor.submit(lambda: None).result()
        sync.start()
    save_tick = mo.ui.refresh(default_interval="5s", label="")
    return (save_tick,)


@app.cell(hide_code=True)
def _(adapter, describe_run, mo, save_tick, sync):
    save_tick  # runs again every few seconds
    _parts = []
    if sync is not None:
        _kind = {"saved": "success", "idle": "neutral", "pending": "info"}.get(sync.status.state, "warn")
        _parts.append(mo.callout(mo.md(sync.status.message), kind=_kind))
    _runs = adapter.repeated_runs()
    if _runs:
        _parts.append(
            mo.callout(
                mo.md(
                    "Some steps of your analysis ran more than once. "
                    + " ".join(describe_run(r) for r in _runs)
                    + " Nothing was removed; this is only a note."
                ),
                kind="warn",
            )
        )
    mo.vstack(_parts + ([save_tick] if save_tick is not None else []))
    return


@app.cell(hide_code=True)
def _(MODE, NotStored, adapter, get_cursor, mo, panel, rt):
    # Every analysis step below goes through record(...). In analyst mode it runs the step and records it. In reviewer
    # mode it does not run anything: it hands back what that step produced at the step the reviewer is on, so each cell
    # shows its own output as it was then, and a cell whose step has not happened yet shows nothing, like a replay.
    if MODE == "analyst":
        from tracker.runtime import _param_fingerprint

        snap = None
        produced = {}  # target name -> the state of the step that produced it

        # The notebook runs again from the top whenever the page is opened, the kernel restarts or the mode is switched
        # back. That run repeats the stored history from its first step, and those steps are not recorded a second time:
        # a call is skipped only while it is the very next step of the stored history (same name, same inputs). The first
        # call that is not ends this, and from then on every step is recorded, so a step a student repeats on purpose
        # is a new step.
        replay = {"on": True, "at": rt._root_state_id, "head": rt._current_state_id}

        def _stored_step(label, args, kwargs):
            """The stored step that this call repeats, or None."""
            try:
                fingerprint = _param_fingerprint(list(args), kwargs)
                for child in rt.storage.load_child_steps(replay["at"]):
                    if child["func_name"] == label and child["param_fingerprint"] == fingerprint:
                        return child
            except Exception:
                pass  # when in doubt, record the step
            return None

        def record(targets, function, *args, name=None, replay_stored=True, **kwargs):
            """Run one analysis step and record it with pmprov.

            pmprov normally records a notebook by rewriting its cells, which needs marimo to be started with a patch.
            A platform such as molab starts marimo itself, so the steps are recorded explicitly instead: this runs
            `function(*args, **kwargs)`, stores its inputs and the outputs under the names in `targets`, and returns the
            result unchanged. `replay_stored=False` is for a step a student asks for (a click), which is always recorded.
            """
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
    else:
        # the whole analysis at the step the reviewer is on (the latest one until they step); this cell re-runs, and
        # with it every cell that uses record(), each time the stepper or a Replay moves the cursor
        snap = panel.snapshot(get_cursor() or adapter.latest_state_id())

        def record(targets, function, *args, name=None, replay_stored=True, **kwargs):
            """The value(s) of `targets` at the reviewer's step; `function` and its arguments are not used."""
            for target in targets:
                mo.stop(snap.status(target) == "not_computed", mo.md(snap.missing(target)))
            values = [snap.get(t) if snap.status(t) == "ok" else NotStored() for t in targets]
            return values[0] if len(values) == 1 else tuple(values)

        def state_of(target):
            return snap.state_id or "analysis"

    return record, snap, state_of


@app.cell(hide_code=True)
def _(MODE, mo, snap):
    mo.stop(MODE != "reviewer")
    mo.callout(mo.md(snap.banner()), kind="info")
    return


@app.cell(hide_code=True)
def _(HERE, Path, pd, project_files, record):
    import lcm

    ACTIVITY = "concept:name"
    CASE_ID = "case:concept:name"
    TIMESTAMP = "time:timestamp"

    def load_event_log(here):
        """The BPI 2017 log as a DataFrame (Parquet copy of BPI_Challenge_2017.xes, all 19 columns).

        The data is looked up (and downloaded on a platform that delivers only the notebook) here, so a reviewer, who
        never runs this step, does not fetch it.
        """
        parquet_path = project_files(here) / "data" / "bpi2017.parquet"
        if not Path(parquet_path).exists():
            raise FileNotFoundError(
                f"{parquet_path} is missing. Put the Parquet copy of the log in the data folder next to the notebook."
            )
        return pd.read_parquet(parquet_path)

    event_log = record(["event_log"], load_event_log, HERE)
    return ACTIVITY, CASE_ID, TIMESTAMP, event_log, lcm


@app.cell(hide_code=True)
def _(ACTIVITY, CASE_ID, event_log, mo, record):
    def summarise_log(log):
        return {
            "cases": int(log[CASE_ID].nunique()),
            "events": len(log),
            "activities": int(log[ACTIVITY].nunique()),
            "columns": log.shape[1],
        }

    log_summary = record(["log_summary"], summarise_log, event_log)
    mo.md(f"""
    **The log:** {log_summary['cases']:,} applications, {log_summary['events']:,} events,
    {log_summary['activities']} activities, {log_summary['columns']} columns. This is the full log, not the smaller one.
    """)
    return


@app.cell(hide_code=True)
def _(ACTIVITY, CASE_ID, TIMESTAMP, lcm, pd):
    # The steps of the analysis, as plain functions. Each one is run through record() where it is used.

    def attribute_coverage(log, activity):
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

    def attributes_with_a_value(coverage):
        return coverage[coverage["events with a value"] > 0].reset_index(drop=True)

    def activities_starting_with(log, prefix):
        return sorted(a for a in log[ACTIVITY].unique() if a.startswith(prefix))

    def case_activity_timestamp(log):
        return log[[CASE_ID, ACTIVITY, TIMESTAMP]]

    def events_carrying(log, attribute):
        """The log reduced to the events that have a value for `attribute` (case, activity and timestamp only)."""
        return log[log[attribute].notna()][[CASE_ID, ACTIVITY, TIMESTAMP]]

    def distinct_activities(log):
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

    def share_of_cases_starting_with(log, activity):
        first = log.sort_values(TIMESTAMP).groupby(CASE_ID)[ACTIVITY].first()
        return float((first == activity).mean() * 100)

    def missing_values_of(coverage, schema):
        attributes = list(schema["attribute"])
        table = coverage[coverage["attribute"].isin(attributes)].assign(
            missing=lambda t: t["events"] - t["events with a value"],
            **{"% missing": lambda t: (100 - t["% of events"]).round(2)},
        )[["attribute", "events", "events with a value", "missing", "% missing"]].reset_index(drop=True)
        outside = coverage[~coverage["attribute"].isin(attributes)]["attribute"].tolist()
        return table, outside

    def attribute_reuse_of(log):
        """For every attribute: on how many different activities does it take a value?"""
        present = log.drop(columns=[ACTIVITY]).notna().groupby(log[ACTIVITY]).any()
        return pd.DataFrame(
            {
                "activities": present.sum(),
                "carried by": present.apply(
                    lambda column: ", ".join(sorted(column.index[column])) if column.sum() <= 8 else "all or most activities"
                ),
            }
        ).sort_values(["activities", "carried by"], ascending=[False, True]).rename_axis("attribute").reset_index()

    return (
        activities_starting_with,
        attribute_coverage,
        attribute_reuse_of,
        attributes_with_a_value,
        case_activity_timestamp,
        distinct_activities,
        draw_map,
        events_carrying,
        missing_values_of,
        share_of_cases_starting_with,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1a. The schema of `A_Create Application`

    The schema of an activity is the set of attributes that take a value on its events. The table shows, for each
    attribute, how many of the events of `A_Create Application` carry it.
    """)
    return


@app.cell(hide_code=True)
def _(attribute_coverage, attributes_with_a_value, event_log, record):
    create_coverage = record(["create_coverage"], attribute_coverage, event_log, "A_Create Application")
    create_schema = record(["create_schema"], attributes_with_a_value, create_coverage)
    return create_coverage, create_schema


@app.cell(hide_code=True)
def _(create_schema, mo, show_table, state_of):
    _state = state_of("create_schema")
    mo.vstack([
        mo.md(f"`A_Create Application` has **{len(create_schema)} attributes** in its schema:"),
        show_table(
            mo.ui.table(create_schema, selection=None, pagination=None),
            artifact_id=_state,
            artifact_name="create_schema",
        ),
    ])
    return


@app.cell(hide_code=True)
def _(activities_starting_with, event_log, record):
    application_activities = record(["application_activities"], activities_starting_with, event_log, "A_")
    return (application_activities,)


@app.cell(hide_code=True)
def _(
    CASE_ID,
    application_activities,
    case_activity_timestamp,
    draw_map,
    event_log,
    record,
    share_of_cases_starting_with,
):
    # The map of the application states over every case. Its first node answers where the schema applies: every
    # case starts with A_Create Application.
    application_log = record(["application_log"], case_activity_timestamp, event_log)
    application_figure, application_meta = record(
        ["application_figure", "application_meta"],
        draw_map, application_log, application_activities, "set_based", True, True, 650,
        name="draw_application_map",
    )
    start_share = record(["start_share"], share_of_cases_starting_with, event_log, "A_Create Application")
    case_count = record(["case_count"], lambda log: int(log[CASE_ID].nunique()), event_log, name="count_cases")
    return application_figure, application_meta, case_count, start_share


@app.cell(hide_code=True)
def _(MODE, application_figure, application_meta, case_count, mo, show_chart, start_share, state_of):
    _state = state_of("application_figure")
    mo.vstack([
        mo.md(
            f"**Set-based map of the application states, all {case_count:,} cases.** "
            f"{start_share:.1f}% of the cases start with `A_Create Application`, so its schema is the one every case "
            f"enters the process with. The map has {application_meta['total_nodes']} nodes, "
            f"{application_meta['terminal_nodes']} of them where cases end."
        ),
        show_chart(
            mo.as_html(application_figure),
            artifact_id=_state,
            artifact_name="map_application_states",
            figure=application_figure if MODE == "analyst" else None,
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1b. Missing values in that schema

    For every attribute of the schema: how many of the events of `A_Create Application` have no value for it.
    The other attributes of the log are not part of this schema, so an empty value there is not a missing value.
    """)
    return


@app.cell(hide_code=True)
def _(create_coverage, create_schema, missing_values_of, record):
    missing_values, outside_schema = record(
        ["missing_values", "outside_schema"], missing_values_of, create_coverage, create_schema,
    )
    return missing_values, outside_schema


@app.cell(hide_code=True)
def _(missing_values, mo, outside_schema, show_table, state_of):
    _state = state_of("missing_values")
    _total = int(missing_values["missing"].sum())
    mo.vstack([
        mo.md(
            f"**{_total} missing values** in {len(missing_values)} attributes. "
            f"Never filled on `A_Create Application`, hence not in its schema: {', '.join(outside_schema)}."
        ),
        show_table(
            mo.ui.table(missing_values, selection=None, pagination=None),
            artifact_id=_state,
            artifact_name="missing_values",
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1c. Attributes re-used across activities

    For every attribute: on how many different activities does it take a value? More than one means the attribute is
    re-used. The maps below are drawn from the events that carry one attribute, so the activities in a map are the
    ones that carry it.
    """)
    return


@app.cell(hide_code=True)
def _(attribute_reuse_of, event_log, record):
    attribute_reuse = record(["attribute_reuse"], attribute_reuse_of, event_log)
    return (attribute_reuse,)


@app.cell(hide_code=True)
def _(attribute_reuse, mo, show_table, state_of):
    _state = state_of("attribute_reuse")
    mo.vstack([
        mo.md(
            f"**{int((attribute_reuse['activities'] > 1).sum())} of {len(attribute_reuse)} attributes** take a value "
            "on more than one activity."
        ),
        show_table(
            mo.ui.table(attribute_reuse, selection=None, pagination=None),
            artifact_id=_state,
            artifact_name="attribute_reuse",
        ),
    ])
    return


@app.cell(hide_code=True)
def _(distinct_activities, draw_map, event_log, events_carrying, record):
    # An attribute that is re-used: OfferID. The log is reduced to the events that carry it.
    offer_id_log = record(["offer_id_log"], events_carrying, event_log, "OfferID")
    offer_id_activities = record(["offer_id_activities"], distinct_activities, offer_id_log)
    offer_id_figure, offer_id_meta = record(
        ["offer_id_figure", "offer_id_meta"],
        draw_map, offer_id_log, offer_id_activities, "set_based", True, False, 650,
        name="draw_offer_id_map",
    )
    return offer_id_activities, offer_id_figure, offer_id_meta


@app.cell(hide_code=True)
def _(MODE, mo, offer_id_activities, offer_id_figure, offer_id_meta, show_chart, state_of):
    _state = state_of("offer_id_figure")
    mo.vstack([
        mo.md(
            f"**`OfferID` is re-used.** The map of the events that carry it has {len(offer_id_activities)} activities: "
            f"{', '.join(offer_id_activities)}. {offer_id_meta['total_nodes']} nodes."
        ),
        show_chart(
            mo.as_html(offer_id_figure),
            artifact_id=_state,
            artifact_name="map_offer_id_carriers",
            figure=offer_id_figure if MODE == "analyst" else None,
        ),
    ])
    return


@app.cell(hide_code=True)
def _(distinct_activities, draw_map, event_log, events_carrying, record):
    # An attribute that is not re-used: CreditScore. Same reduction, one activity left.
    credit_score_log = record(["credit_score_log"], events_carrying, event_log, "CreditScore")
    credit_score_activities = record(["credit_score_activities"], distinct_activities, credit_score_log)
    credit_score_figure, credit_score_meta = record(
        ["credit_score_figure", "credit_score_meta"],
        draw_map, credit_score_log, credit_score_activities, "set_based", True, False, 400,
        name="draw_credit_score_map",
    )
    return credit_score_activities, credit_score_figure, credit_score_meta


@app.cell(hide_code=True)
def _(MODE, credit_score_activities, credit_score_figure, mo, show_chart, state_of):
    _state = state_of("credit_score_figure")
    mo.vstack([
        mo.md(
            f"**`CreditScore` is not re-used.** The map of the events that carry it has "
            f"{len(credit_score_activities)} activity: {', '.join(credit_score_activities)}."
        ),
        show_chart(
            mo.as_html(credit_score_figure),
            artifact_id=_state,
            artifact_name="map_credit_score_carriers",
            figure=credit_score_figure if MODE == "analyst" else None,
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Map explorer

    The same maps for any activities, as in the original app: choose the activities and the abstraction, then refresh.
    """)
    return


@app.cell(hide_code=True)
def _(MODE, distinct_activities, event_log, mo):
    mo.stop(MODE != "analyst")
    _all_activities = distinct_activities(event_log)
    get_view, set_view = mo.state(None)
    explorer_activities = mo.ui.multiselect(options=_all_activities, value=[a for a in _all_activities if a.startswith("O_")], label="Activities")
    explorer_builder = mo.ui.dropdown(
        options={"Set-Based": "set_based", "Sequence-Based": "sequence_based", "Last-Activity-Based": "last_activity_based"},
        value="Set-Based",
        label="Generic map",
    )
    explorer_loops = mo.ui.switch(value=True, label="Allow self-loops")
    explorer_empty = mo.ui.switch(value=True, label="Visualize empty traces")

    def _commit(_):
        set_view(
            {
                "activities": list(explorer_activities.value),
                "builder": explorer_builder.value,
                "loops": explorer_loops.value,
                "empty": explorer_empty.value,
            }
        )

    explorer_refresh = mo.ui.button(label="Refresh visualization", kind="success", on_click=_commit)
    mo.vstack([explorer_activities, mo.hstack([explorer_builder, explorer_loops, explorer_empty], justify="start", gap=2), explorer_refresh])
    return (get_view,)


@app.cell(hide_code=True)
def _(case_activity_timestamp, draw_map, event_log, get_view, mo, record):
    _view = get_view()
    mo.stop(_view is None, mo.md("*Choose the activities, then click Refresh.*"))

    explorer_log = record(["explorer_log"], case_activity_timestamp, event_log, replay_stored=False)
    explorer_figure, explorer_meta = record(
        ["explorer_figure", "explorer_meta"],
        draw_map, explorer_log, _view["activities"], _view["builder"], _view["loops"], _view["empty"], 650,
        name="draw_explorer_map", replay_stored=False,
    )
    return explorer_figure, explorer_meta


@app.cell(hide_code=True)
def _(explorer_figure, explorer_meta, mo, show_chart, state_of):
    _state = state_of("explorer_figure")
    _nodes = explorer_meta["total_nodes"]
    mo.vstack([
        mo.callout(
            mo.md(
                f"This map has **{_nodes:,} nodes**. A map this large is slow to draw, hover and annotate; "
                "choose fewer activities or the set-based abstraction for a readable one."
            ),
            kind="warn",
        ) if _nodes > 1000 else mo.md(f"{_nodes} nodes."),
        show_chart(
            mo.as_html(explorer_figure),
            artifact_id=_state,
            artifact_name="map_explorer",
            figure=explorer_figure,
        ),
    ])
    return


@app.cell(hide_code=True)
def _(MODE, mo, show_chart, snap, state_of):
    # the explorer's controls only exist in analyst mode; a reviewer sees the map the analyst last drew, as it was
    mo.stop(MODE != "reviewer")
    mo.stop(snap.status("explorer_figure") != "ok", mo.md(snap.missing("explorer_figure")))
    mo.vstack([
        mo.md(f"{snap.get('explorer_meta')['total_nodes']:,} nodes."),
        show_chart(
            mo.as_html(snap.get("explorer_figure")),
            artifact_id=state_of("explorer_figure"),
            artifact_name="map_explorer",
        ),
    ])
    return


if __name__ == "__main__":
    app.run()
