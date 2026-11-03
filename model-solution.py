# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.2",
#     "pmprov[duckdb,parquet,graph]>=0.10.0",
#     "marimo-pmprov[pdf]>=0.4.3",
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
    # Model solution: what does a loan application carry?

    This tutorial shows one way to answer the first exploratory task of the assignment on the **BPI Challenge 2017** event log
    (a bank's loan applications, 31,509 of them). It is a **replay**: everything you see was done with the tools of the student
    notebook, step by step, and recorded on the course server. Each table and map below is one recorded step, and the notes in the
    side panel were written on the output they explain.

    **The three questions** (the full assignment, with the background of the log, is in `assignment.md`)

    1. Which data (attributes) does the first activity, `A_Create Application`, carry?
    2. Which of those attributes are sometimes empty?
    3. Is any attribute used by more than one activity?

    **How to read it**

    - Use the **arrows in the side panel** to move through the analysis one step at a time. Every section of this page shows its
      table or map *as it was at that step*, and sections that come later are still empty.
    - Open a **note** in the side panel and press **Replay**: you jump to the step where it was written, and the table or map it is
      about is highlighted.
    - You cannot change anything here. To do the analysis yourself, use the student notebook.
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import shutil as _shutil
    import sys as _sys
    import tempfile as _tempfile
    import urllib.request as _request
    from pathlib import Path

    from tracker.runtime import RuntimeTracker
    from tracker.storage import DuckDBSQLiteBackend
    from provenance_widget.pmprov_adapter import PmprovAdapter
    from provenance_widget.widget import ProvenancePanel
    from provenance_widget.display import show_chart, show_table
    from provenance_widget.portable import relocate_artifacts
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
        downloaded from the repository into a temporary folder (small files each time, so they are current)."""
        local = HERE / relative
        if local.exists():
            return local
        cached = Path(_tempfile.gettempdir()) / "bpm-project-files" / relative
        if refresh or not cached.exists():
            cached.parent.mkdir(parents=True, exist_ok=True)
            part = cached.with_name(cached.name + ".part")
            with _request.urlopen(RAW_URL + relative, timeout=300) as response, open(part, "wb") as out:
                _shutil.copyfileobj(response, out)
            part.replace(cached)
        return cached

    _kit_file = project_file("bpm_kit.py", refresh=True)
    if str(_kit_file.parent) not in _sys.path:
        _sys.path.insert(0, str(_kit_file.parent))
    import bpm_kit as kit

    return (
        DuckDBSQLiteBackend,
        PmprovAdapter,
        ProvenancePanel,
        RuntimeTracker,
        kit,
        mo,
        Sync,
        project_file,
        relocate_artifacts,
        show_chart,
        show_table,
    )


@app.cell(hide_code=True)
def _(DuckDBSQLiteBackend, RuntimeTracker, Sync, kit, mo, relocate_artifacts):
    # The solution is an analysis stored on the course server, read exactly as a student's own work is: it was made with the tools of
    # the student notebook under this key, and its course was then closed, so nothing can be saved over it any more. This key can
    # only read it.
    import os as _os
    import shutil as _shutil
    import tempfile as _tempfile
    from pathlib import Path as _Path

    _url = _os.environ.get("PMPROV_SYNC_URL", "https://provenance.alvispace.com")
    _key = "model-solution-tutorial-7bmavmds"
    _folder = _Path(_tempfile.gettempdir()) / "bpm-model-solution"
    _shutil.rmtree(_folder, ignore_errors=True)  # always the stored copy, never an older download
    (_folder / "artifacts").mkdir(parents=True)
    _sync = Sync(_url, _key, _folder)
    _outcome = _sync.restore()
    mo.stop(
        _outcome != "restored",
        mo.callout(
            mo.md(
                "The model solution could not be loaded from the course server"
                + (f": {_sync.status.message}" if _sync.status.message else ".")
                + " Check your connection and run the notebook again."
            ),
            kind="danger",
        ),
    )
    relocate_artifacts(_folder / "provenance.db", _folder / "artifacts")
    _storage = DuckDBSQLiteBackend(db_path=_folder / "provenance.db", artifact_dir=_folder / "artifacts")
    _history = _storage.find_latest_history_by_name(kit.HISTORY_NAME)
    mo.stop(_history is None, mo.callout(mo.md("The recorded solution could not be found."), kind="danger"))
    # resume the stored history without recording anything: this notebook only reads
    rt = RuntimeTracker.resume(_storage, _history, session_id="reviewer")
    return (rt,)


@app.cell(hide_code=True)
def _(PmprovAdapter, ProvenancePanel, mo, rt):
    adapter = PmprovAdapter(rt)
    panel = ProvenancePanel(source=adapter, mode="reviewer")
    # build the tree now, not in the background, so the first snapshot below already knows its step
    panel.refresh()
    # every step of the stepper, and every Replay on a note, moves this cursor; the cells that call get_cursor() run again
    get_cursor = panel.reactive_cursor(mo.state)
    return adapter, get_cursor, panel


@app.cell(hide_code=True)
def _(mo, panel):
    # mo.sidebar(...) has to be the last bare expression of its cell to render
    mo.sidebar(panel.sidebar())
    return


@app.cell(hide_code=True)
def _(adapter, get_cursor, kit, mo, panel):
    # Every table and map below calls record(...). Here it runs nothing: it hands back what that step produced at the step the
    # reader is on, so each cell shows its own output as it was then, and a cell whose step has not happened yet shows nothing.
    snap = panel.snapshot(get_cursor() or adapter.latest_state_id())
    record, state_of = kit.reviewer_recorder(snap, mo)
    return record, snap, state_of


@app.cell(hide_code=True)
def _(mo, snap):
    mo.callout(mo.md(snap.banner()), kind="info")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 0. A first look at the event log

    Before drawing anything, look at what is in the log: how big it is, which activities it records and what data each event
    carries. An event log is a table with one row per event. Each event says *which case* it belongs to (here, one loan
    application), *which activity* happened and *when*, plus further attributes.
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
            "**The activities.** The assignment says the names start with `A_` (the state of the application), `O_` (the state of an "
            "offer) or `W_` (a piece of work done by an employee). The table groups them that way and shows how many events each "
            "has and in what share of the cases it occurs."
        ),
        show_table(
            mo.ui.table(activities, selection=None, pagination=None),
            artifact_id=_state,
            artifact_name="activity_overview",
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Two things stand out. Some activities occur in **every** case (`A_Create Application`, `A_Concept`, `A_Accepted`,
    `O_Create Offer`, `O_Created`, `W_Complete application`: 100%), while others are rare, such as `A_Denied` or
    `W_Assess potential fraud`. And the three families look like three small processes that run side by side.
    """)
    return


@app.cell(hide_code=True)
def _(event_log, kit, mo, record, show_table, state_of):
    attributes = record(["attributes"], kit.attribute_overview, event_log)
    _state = state_of("attributes")
    _full = int((attributes["% of events"] == 100).sum())
    mo.vstack([
        mo.md(
            f"**The attributes.** Every column of the log, with the number of events that have a value for it. "
            f"{_full} of the {len(attributes)} columns are filled on every event; the others are filled on only a small share."
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
    _intro = mo.md(
        "**The first events, as they are stored.** The offer columns (`OfferID`, `CreditScore`, ...) are empty here, as they are "
        "on most rows of the log. Scroll sideways and look at which columns have values."
    )
    # a table too wide to be kept with the analysis is not stored; the student notebook shows it
    mo.vstack([_intro, show_table(
        mo.ui.table(sample, selection=None, page_size=10), artifact_id=_state, artifact_name="log_sample",
    ) if not isinstance(sample, kit.NotStored) else mo.callout(mo.md("This table is not kept with the recorded analysis. Run the student notebook to see it."), kind="neutral")])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **What we take from the first look.** The log mixes events of very different kinds, and the columns that describe an offer
    (`OfferID`, `CreditScore`, `OfferedAmount`, ...) have a value on only a few percent of the events. So the data an event carries
    depends on *which activity it is*. That is exactly what the three questions ask about.

    ## 1. Which attributes does an activity carry?
    """)
    return


@app.cell(hide_code=True)
def _(event_log, kit, mo, record, show_table, state_of):
    coverage = record(["coverage"], kit.attribute_coverage, event_log, None)
    _state = state_of("coverage")
    _carried = int((coverage["events with a value"] > 0).sum())
    mo.vstack([
        mo.md(
            "**The attributes of one activity.** For each attribute, how many of **one activity's** events have a value. The attributes "
            f"with at least one value are what that activity carries: here {_carried} of {len(coverage)}. The first activity looked at "
            "is `A_Create Application`, later `O_Create Offer`: step through the analysis to see each."
        ),
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
    **Answers to 1a and 1b.** For `A_Create Application` eleven attributes have a value: eight describe *any* event (who did it,
    when, which event it is) and three describe the *loan application* itself (`LoanGoal`, `ApplicationType`, `RequestedAmount`).
    **None** of them is ever empty on this activity. The others are empty here, but they are not part of its schema, so that is not
    a *missing* value: they are offer attributes.

    ## 2. Reading the process with maps

    A table cannot show **order**. For that we use a *process map* of the Linear Continuous Process Mapper (LC map). It draws
    every case as a path from left to right; cases that behave alike share a path, and the **width of a band** is the number of
    cases that follow it. Hover over a band or a node for the numbers.

    The map comes in three abstractions. We use the **set-based** one: a node stands for the *set* of activities a case has done so
    far, whatever the order, which keeps the map small and readable.

    A map shows the order of activities, **not attributes**. To use one for an attribute question we reduce the log to the events
    that carry the attribute: the activities in such a map are then exactly the activities that carry it.

    The maps below were drawn one after another with the map explorer of the student notebook; the cell shows the one the analysis
    has reached. The first is the map of the application states (`A_`), then the offer states (`O_`), then the events that carry
    `OfferID`, then the events that carry `CreditScore`. Move the arrows of the side panel to see each of them.
    """)
    return


@app.cell(hide_code=True)
def _(event_log, kit, mo, record, show_chart, state_of):
    explorer_log = record(["explorer_log"], kit.case_activity_timestamp, event_log)
    explorer_figure, explorer_meta = record(
        ["explorer_figure", "explorer_meta"], kit.draw_map, explorer_log, None, "set_based", True, True, 650,
        name="draw_explorer_map",
    )
    _state = state_of("explorer_figure")
    mo.vstack([
        mo.md(f"**Set-based map at this step.** {explorer_meta['total_nodes']} nodes, {explorer_meta['terminal_nodes']} of them where cases end."),
        show_chart(
            mo.as_html(explorer_figure),
            artifact_id=_state,
            artifact_name="process_map",
            figure=None,
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. The answers

    1. **Schema of `A_Create Application`:** eleven attributes: eight that describe any event and three that describe the loan
       application (`LoanGoal`, `ApplicationType`, `RequestedAmount`). Every application starts with this activity, so it is the data
       an application enters the process with.
    2. **Missing values:** none. Every attribute of the schema is filled on every event. The attributes that are empty on this
       activity are offer attributes that do not belong to its schema.
    3. **Attributes used by more than one activity:** `OfferID` is re-used: the map of the events that carry it shows the offer
       states after `O_Create Offer`. `CreditScore` is not: its map shows a single activity, `O_Create Offer`.

    **How we got there:** a first look at the log told us the data depends on the activity; a table per activity gave the numbers;
    and the maps showed *where* an attribute lives, by drawing only the events that carry it. In the side panel, each note says what
    one table or map shows. Now do the same on your own: the student notebook has the same tables and the map explorer, and you can
    reach these findings yourself.
    """)
    return


if __name__ == "__main__":
    app.run()
