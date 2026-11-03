# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.2",
#     "pmprov[duckdb,parquet,graph]>=0.10.0",
#     "marimo-pmprov[pdf]>=0.4.4",
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

    You will explore a real event log of a bank's loan approval process (the **BPI Challenge 2017**: 31,509 loan applications,
    1.2 million events) and write down what you find. First you look at the log, then you use **process maps** to understand it.

    **How to use this notebook**

    1. **Enter your key** below. If you worked here before, your earlier work comes back by itself.
    2. **Take a first look** at the event log (section 1): its activities, its attributes and a few events.
    3. **Explore with maps** (section 2): choose which activities to draw and press *Refresh visualization*.
    4. **Write down what you find** in the side panel: press **Pick**, click the table or the map you mean, write your note and
       press **Add**. Your notes are what you hand in.

    Your work is saved automatically. You can close this page and come back with the same key.

    **The three questions** (the background of the log is in `assignment.md`)

    1. Which data (attributes) does the first activity, `A_Create Application`, carry?
    2. Which of those attributes are sometimes empty?
    3. Is any attribute used by more than one activity?

    **A hint on maps.** A map shows the *order of activities*, not attributes. To use a map for an attribute question, tell the map
    to draw only the events that have a value for that attribute: the activities in the map are then exactly the activities that
    carry it.
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import shutil as _shutil
    import sys as _sys
    import tempfile as _tempfile
    import urllib.request as _request
    import warnings as _warnings
    import os as _os
    from pathlib import Path

    from tracker import init_marimo
    from provenance_widget.pmprov_adapter import PmprovAdapter
    from provenance_widget.widget import ProvenancePanel
    from provenance_widget.display import show_chart, show_table
    from provenance_widget.portable import relocate_artifacts, zip_provenance
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
    RAW_URL = "https://raw.githubusercontent.com/alvarobernal2412/bpm/main/"

    def project_file(relative, refresh=False):
        """A file of this project. Next to the notebook when the whole folder is there (a local checkout). A platform that
        delivers only the notebook file, such as molab opening it from GitHub, does not bring the others, so they are
        downloaded from the repository into a temporary folder (the log once, the small files each time, so they are current)."""
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

    # The course server that keeps each student's work. Set PMPROV_SYNC_URL to another address, or to an empty value to
    # work without a server (the work then stays in ./provenance next to the notebook).
    SYNC_URL = _os.environ.get("PMPROV_SYNC_URL", "https://provenance.alvispace.com")

    # pmprov warns that its cell rewriting is not active; the steps are recorded explicitly with record() below
    _warnings.filterwarnings("ignore", message=r"init_marimo\(\) was called but patch_marimo_ast_compile")

    return (
        HERE,
        PmprovAdapter,
        Path,
        ProvenancePanel,
        SYNC_URL,
        Sync,
        describe_run,
        init_marimo,
        kit,
        mo,
        relocate_artifacts,
        show_chart,
        show_table,
        zip_provenance,
    )


@app.cell(hide_code=True)
def _(SYNC_URL, kit, mo):
    key_box = mo.ui.anywidget(kit.KeyBox()) if SYNC_URL else None
    mo.vstack([mo.md("### Your key"), key_box]) if key_box else mo.md("*Working without a server: your work stays in this notebook's folder.*")
    return (key_box,)


@app.cell(hide_code=True)
def _(HERE, Path, SYNC_URL, Sync, key_box, kit, mo):
    # With a server, nothing starts until there is a key; then the student's earlier work is brought back before
    # anything opens the provenance database.
    import os as _os

    sync = None
    if SYNC_URL:
        _key = (key_box.value.get("key") or "").strip()
        mo.stop(not _key, mo.callout(mo.md("Enter your key above to start."), kind="info"))
        PROVENANCE_DIR = kit.session_folder(_key)
        sync = Sync(SYNC_URL, _key, PROVENANCE_DIR)
        sync.restore()
        mo.stop(sync.status.state == "unauthorized", mo.callout(mo.md(sync.status.message), kind="danger"))
    else:
        PROVENANCE_DIR = Path(_os.environ.get("PMPROV_DIR") or HERE / "provenance")
    (PROVENANCE_DIR / "artifacts").mkdir(parents=True, exist_ok=True)
    return PROVENANCE_DIR, sync


@app.cell(hide_code=True)
def _(PROVENANCE_DIR, init_marimo, kit, relocate_artifacts):
    # a history that was downloaded from another machine points at that machine's folders
    relocate_artifacts(PROVENANCE_DIR / "provenance.db", PROVENANCE_DIR / "artifacts")
    rt = init_marimo(
        history_name=kit.HISTORY_NAME,
        branch_name="main",
        db_path=str(PROVENANCE_DIR / "provenance.db"),
        artifact_dir=str(PROVENANCE_DIR / "artifacts"),
        fresh=False,  # continue the stored history of this name after a restart
    )
    return (rt,)


@app.cell(hide_code=True)
def _(PROVENANCE_DIR, mo, rt, zip_provenance):
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
def _(PmprovAdapter, ProvenancePanel, rt):
    adapter = PmprovAdapter(rt)
    # the student can annotate, edit and export; there is no other mode in this notebook
    panel = ProvenancePanel(source=adapter, mode="analyst", tabs=["curated"])
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
    mo.vstack(_parts + [save_tick])
    return


@app.cell(hide_code=True)
def _(adapter, kit, rt):
    # Every step of the analysis goes through record(...): it runs the step and stores it, so the notes you write can be attached
    # to the table or the map that produced them, and your work can be read back later step by step.
    record, state_of = kit.analyst_recorder(rt, adapter)
    return record, state_of


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. A first look at the event log

    An event log is a table with one row per **event**. Each event says *which case* it belongs to (here, one loan application),
    *which activity* happened and *when*, plus further attributes. Before you draw anything, find out what is in it.
    """)
    return


@app.cell(hide_code=True)
def _(kit, mo, record):
    event_log = record(["event_log"], kit.load_event_log, "data/bpi2017.parquet")
    log_summary = record(["log_summary"], kit.summarise_log, event_log)
    mo.md(f"""
    **The log:** {log_summary['cases']:,} applications, {log_summary['events']:,} events, {log_summary['activities']} activities,
    {log_summary['columns']} columns. This is the full log, not the smaller one.
    """)
    return event_log, log_summary


@app.cell(hide_code=True)
def _(event_log, kit, mo, record, show_table, state_of):
    activities = record(["activities"], kit.activity_overview, event_log)
    _state = state_of("activities")
    mo.vstack([
        mo.md(
            "**The activities.** Their names start with `A_` (the state of the application), `O_` (the state of an offer) or `W_` "
            "(a piece of work done by an employee). How many events does each have, and in what share of the cases does it occur?"
        ),
        show_table(
            mo.ui.table(activities, selection=None, pagination=None),
            artifact_id=_state,
            artifact_name="activity_overview",
        ),
    ])
    return


@app.cell(hide_code=True)
def _(event_log, kit, mo, record, show_table, state_of):
    attributes = record(["attributes"], kit.attribute_overview, event_log)
    _state = state_of("attributes")
    mo.vstack([
        mo.md(
            "**The attributes.** Every column of the log, with the number of events that have a value for it. "
            "Which columns are filled on every event, and which only on a few?"
        ),
        show_table(
            mo.ui.table(attributes, selection=None, pagination=None),
            artifact_id=_state,
            artifact_name="attribute_overview",
        ),
    ])
    return


@app.cell(hide_code=True)
def _(event_log, kit, mo, record, show_table, state_of):
    sample = record(["log_sample"], kit.log_sample, event_log, 100)
    _state = state_of("log_sample")
    mo.vstack([
        mo.md("**The first events, as they are stored.** Scroll sideways and look at which columns have a value."),
        show_table(
            mo.ui.table(sample, selection=None, page_size=10),
            artifact_id=_state,
            artifact_name="log_sample",
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### The attributes of one activity

    Choose an activity to see, for each attribute, how many of **its** events have a value. The attributes with at least one value
    are what that activity carries.
    """)
    return


@app.cell(hide_code=True)
def _(event_log, kit, mo):
    _names = kit.distinct_activities(event_log)
    get_coverage_view, set_coverage_view = mo.state(None)
    coverage_activity = mo.ui.dropdown(options=_names, value="A_Create Application", label="Activity")
    coverage_button = mo.ui.button(
        label="Show its attributes", kind="success", on_click=lambda _: set_coverage_view(coverage_activity.value)
    )
    mo.hstack([coverage_activity, coverage_button], justify="start", gap=2, align="end")
    return (get_coverage_view,)


@app.cell(hide_code=True)
def _(event_log, get_coverage_view, kit, mo, record, show_table, state_of):
    _activity = get_coverage_view()
    mo.stop(_activity is None, mo.md("*Choose an activity, then press the button.*"))
    # a step you ask for is always recorded, even when you ask for the same one twice
    coverage = record(["coverage"], kit.attribute_coverage, event_log, _activity, replay_stored=False)
    _state = state_of("coverage")
    mo.vstack([
        mo.md(f"**Attributes of `{_activity}`:** {int((coverage['events with a value'] > 0).sum())} of {len(coverage)} have a value."),
        show_table(
            mo.ui.table(coverage, selection=None, pagination=None),
            artifact_id=_state,
            artifact_name="attributes_of_activity",
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Explore with process maps

    A **process map** (a Linear Continuous Process Mapper map) draws every case as a path from left to right. Cases that behave
    alike share a path, and the **width of a band** is the number of cases that follow it. Hover over a band or a node for the
    numbers, and drag the nodes to arrange the map.

    Choose what to draw and press **Refresh visualization**:

    - **Activities:** a whole family (application states, offer states, workflow activities), all of them, or a list you pick.
    - **Only events that have a value for:** keep only the events that carry one attribute. The map then shows exactly the
      activities that carry it.
    - **Map type:** *set-based* is the smallest and the easiest to read; the other two keep more detail and can be large.
    """)
    return


@app.cell(hide_code=True)
def _(event_log, kit, mo):
    _all_activities = kit.distinct_activities(event_log)
    _attributes = [c for c in event_log.columns if c not in (kit.CASE_ID, kit.ACTIVITY, kit.TIMESTAMP)]
    get_view, set_view = mo.state(None)
    explorer_family = mo.ui.dropdown(
        options={
            "Application states (A_)": "A_",
            "Offer states (O_)": "O_",
            "Workflow activities (W_)": "W_",
            "All activities": "",
            "A list I choose": None,
        },
        value="Application states (A_)",
        label="Activities",
    )
    explorer_pick = mo.ui.multiselect(options=_all_activities, value=[], label="My list (used when you choose “A list I choose”)")
    explorer_attribute = mo.ui.dropdown(
        options={"No filter: all events": None, **{name: name for name in sorted(_attributes)}},
        value="No filter: all events",
        label="Only events that have a value for",
    )
    explorer_builder = mo.ui.dropdown(
        options={"Set-based": "set_based", "Sequence-based": "sequence_based", "Last-activity-based": "last_activity_based"},
        value="Set-based",
        label="Map type",
    )
    explorer_loops = mo.ui.switch(value=True, label="Show activities that repeat (self-loops)")
    explorer_empty = mo.ui.switch(value=True, label="Show cases with no events left")

    def _commit(_):
        set_view(
            {
                "family": explorer_family.value,
                "picked": list(explorer_pick.value),
                "attribute": explorer_attribute.value,
                "builder": explorer_builder.value,
                "loops": explorer_loops.value,
                "empty": explorer_empty.value,
            }
        )

    explorer_refresh = mo.ui.button(label="Refresh visualization", kind="success", on_click=_commit)
    mo.vstack([
        mo.hstack([explorer_family, explorer_attribute, explorer_builder], justify="start", gap=2, align="end"),
        explorer_pick,
        mo.hstack([explorer_loops, explorer_empty], justify="start", gap=2),
        explorer_refresh,
    ])
    return (get_view,)


@app.cell(hide_code=True)
def _(event_log, get_view, kit, mo, record):
    _view = get_view()
    mo.stop(_view is None, mo.md("*Choose what to draw, then press Refresh visualization.*"))

    # every map you ask for is a new step, even when it repeats an earlier one
    if _view["attribute"]:
        explorer_log = record(["explorer_log"], kit.events_carrying, event_log, _view["attribute"], replay_stored=False)
        explorer_activities = record(["explorer_activities"], kit.distinct_activities, explorer_log, replay_stored=False)
    else:
        explorer_log = record(["explorer_log"], kit.case_activity_timestamp, event_log, replay_stored=False)
        explorer_activities = (
            _view["picked"] if _view["family"] is None else kit.activities_starting_with(event_log, _view["family"])
        )
    mo.stop(not explorer_activities, mo.callout(mo.md("Pick at least one activity for your list."), kind="warn"))
    explorer_figure, explorer_meta = record(
        ["explorer_figure", "explorer_meta"],
        kit.draw_map, explorer_log, explorer_activities, _view["builder"], _view["loops"], _view["empty"], 650,
        name="draw_explorer_map", replay_stored=False,
    )
    return explorer_activities, explorer_figure, explorer_meta


@app.cell(hide_code=True)
def _(explorer_activities, explorer_figure, explorer_meta, get_view, mo, show_chart, state_of):
    _state = state_of("explorer_figure")
    _nodes = explorer_meta["total_nodes"]
    _attribute = get_view()["attribute"]
    mo.vstack([
        mo.md(
            (f"**Map of the events that have a value for `{_attribute}`.** " if _attribute else "**Map.** ")
            + f"{len(explorer_activities)} {'activity' if len(explorer_activities) == 1 else 'activities'}: {', '.join(explorer_activities)}."
        ),
        mo.callout(
            mo.md(
                f"This map has **{_nodes:,} nodes**. A map this large is slow to draw, hover and annotate; "
                "choose fewer activities or the set-based map type for a readable one."
            ),
            kind="warn",
        ) if _nodes > 1000 else mo.md(f"{_nodes} nodes."),
        show_chart(
            mo.as_html(explorer_figure),
            artifact_id=_state,
            artifact_name="process_map",
            figure=explorer_figure,
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Write down what you find

    Your notes are your answers. For each of the three questions, attach a note to the table or the map that shows it:

    1. In the side panel press **Pick**, then click the table or the map (or a part of it) that you mean.
    2. Write what it shows and why it answers the question, then press **Add**.
    3. Add tags to group your notes, for example one per question.

    You can draw as many maps as you like: each one is a step in your analysis, and your notes stay attached to the step they were
    written on. Everything is saved for you.
    """)
    return


if __name__ == "__main__":
    app.run()
