# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.2",
#     "pmprov[duckdb,parquet,graph]>=0.10.0",
#     "marimo-pmprov[pdf]>=0.5.0",
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
    # Loan applications: lifecycles and outcomes with process maps

    In this notebook you answer Tasks 8, 9 and 10 of the assignment on the **BPI Challenge 2017** event log (31,509 loan
    applications, 1.2 million events) with linear continuous process maps, and you write down your intents and findings as annotations.
    Work through the tutorial notebook first: it explains the elements of a map, its settings and how to write annotations.

    **The tasks**

    - **Task 8.** Keep only the Loan Application lifecycle (all activities starting with `A_`) in the process map and write down at
      least three interesting observations.
    - **Task 9.** Repeat Task 8 for the Offer lifecycle: keep the activities starting with `O_`, but not `O_Create Offer`.
    - **Task 10.** Create a visualization of the case outcome distribution of the log. The set of outcomes must be pairwise
      mutually exclusive and complete. Briefly reflect on the result.

    **How to use this notebook**

    1. **Enter your key** below. If you worked here before, your earlier work comes back by itself.
    2. **Look at the event log** (section 1): its size and its activities.
    3. **Draw maps** with the map explorer (section 2): choose the settings and press **Refresh visualization**. Every map you
       draw is recorded as a step of your analysis.
    4. **Write your annotations** in the side panel (section 3 explains how). Your annotations are what you hand in.

    Your work is saved automatically. You can close this page and continue later with the same key.
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
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
    from provenance_widget.display import show_chart, show_table
    from provenance_widget.portable import relocate_artifacts, zip_provenance
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

    # The course server that keeps each student's work. Set PMPROV_SYNC_URL to another address, or to an empty value to work
    # without a server (the work then stays in ./provenance next to the notebook).
    SYNC_URL = _os.environ.get("PMPROV_SYNC_URL", "https://provenance.alvispace.com")

    # pmprov warns that its cell rewriting is not active; the steps are recorded explicitly with record() below
    _warnings.filterwarnings("ignore", message=r"init_marimo\(\) was called but patch_marimo_ast_compile")
    return (
        HERE,
        Path,
        PmprovAdapter,
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
    mo.vstack([mo.md("### Your key"), key_box]) if key_box is not None else mo.md("*Working without a server: your work stays in this notebook's folder.*")
    return (key_box,)


@app.cell(hide_code=True)
def _(HERE, Path, SYNC_URL, Sync, key_box, kit, mo):
    # With a server, nothing starts until there is a key; then the student's earlier work is brought back before anything opens
    # the provenance database.
    sync = None
    if SYNC_URL:
        _key = (key_box.value.get("key") or "").strip()
        mo.stop(not _key, mo.callout(mo.md("Enter your key above to start."), kind="info"))
        PROVENANCE_DIR = kit.session_folder(_key)
        sync = Sync(SYNC_URL, _key, PROVENANCE_DIR)
        sync.restore()
        mo.stop(sync.status.state == "unauthorized", mo.callout(mo.md(sync.status.message), kind="danger"))
    else:
        PROVENANCE_DIR = Path(kit.os.environ.get("PMPROV_DIR") or HERE / "provenance")
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
        """The history as one small zip file: the steps and annotations, and the values small enough to carry."""
        rt.storage._executor.submit(lambda: None).result()  # let the writes that are still queued land first
        data, _left_out = zip_provenance(PROVENANCE_DIR)
        return data

    mo.vstack([
        mo.md(
            "Your work is saved for you. To keep a copy on your own computer as well, download it here "
            "(the file contains every step, annotation, table and map)."
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
                    + " Nothing was removed; this is only a remark."
                ),
                kind="warn",
            )
        )
    mo.vstack(_parts + [save_tick])
    return


@app.cell(hide_code=True)
def _(adapter, kit, rt):
    # Every step of the analysis goes through record(...): it runs the step and stores it, so that an annotation can be attached to the
    # table or map that the step produced, and the analysis can be replayed step by step.
    record, state_of = kit.analyst_recorder(rt, adapter)
    return record, state_of


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. The event log

    The line below gives the size of the log. The table lists every activity with its family (`A_`: a state of the application,
    `O_`: a state of an offer, `W_`: a piece of work done by an employee), the number of events it has, the number of applications
    (cases) in which it occurs and that number as a share of all applications.
    """)
    return


@app.cell(hide_code=True)
def _(kit, mo, record):
    event_log = record(["event_log"], kit.load_event_log, kit.BPI2017)
    log_summary = record(["log_summary"], kit.summarise_log, event_log)
    mo.md(
        f"**The log:** {log_summary['cases']:,} applications, {log_summary['events']:,} events, "
        f"{log_summary['activities']} activities, {log_summary['columns']} columns."
    )
    return (event_log,)


@app.cell(hide_code=True)
def _(event_log, kit, mo, record, show_table, state_of):
    activities = record(["activities"], kit.activity_overview, event_log)
    show_table(
        mo.ui.table(activities, selection=None, pagination=None),
        artifact_id=state_of("activities"),
        artifact_name="activity_overview",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Map explorer

    Choose the settings and press **Refresh visualization**. The line next to the button tells you whether the map on screen
    matches the settings. The settings are explained in the tutorial notebook:

    - **Abstraction:** set-based, last-activity-based or sequence-based.
    - **Each path is:** a loan application, or one offer (the offer events grouped by `OfferID`).
    - **Show self-loops** and **Show empty traces.**
    - **Quick selection** and **Activities to draw:** the buttons select a whole family; the list below them can be edited.
    - **Activity folding:** up to three folds, each with a name and the activities it replaces.

    Every map you draw is a new step of your analysis, even when it repeats an earlier one. Maps with many activities (all of them,
    or the workflow activities) take several seconds to draw.
    """)
    return


@app.cell(hide_code=True)
def _(event_log, kit):
    explorer_names = kit.distinct_activities(event_log)
    explorer_notions = kit.case_notions_of(event_log)
    return explorer_names, explorer_notions


@app.cell(hide_code=True)
def _(adapter, kit, mo):
    # draft: what the controls are built from (changed by the quick selection); drawn: what the map shows (changed by Refresh).
    # When the page is opened again, the explorer comes back as the student left it: the settings of the last map in the stored
    # history. That map is drawn again (it is already a step of the history, so it is not recorded a second time).
    resume = {"settings": kit.last_map_settings(adapter)}
    get_draft, set_draft = mo.state(resume["settings"])
    get_drawn, set_drawn = mo.state(resume["settings"])
    return get_draft, get_drawn, resume, set_draft, set_drawn


@app.cell(hide_code=True)
def _(explorer_names, explorer_notions, get_draft, kit, mo):
    map_controls = kit.map_controls(mo, explorer_names, get_draft() or {"activities": []}, explorer_notions)
    return (map_controls,)


@app.cell(hide_code=True)
def _(explorer_names, kit, map_controls, mo, set_draft, set_drawn):
    def _select(activities):
        current = kit.settings_from(map_controls.value, explorer_names)
        set_draft({**current, "activities": None if set(activities) == set(explorer_names) else activities})

    preset_buttons = mo.ui.array(
        [mo.ui.button(label=label, on_click=lambda _, a=acts: _select(a)) for label, acts in kit.activity_presets(explorer_names).items()]
    )
    refresh_button = mo.ui.button(
        label="Refresh visualization", kind="success",
        on_click=lambda _: set_drawn(kit.settings_from(map_controls.value, explorer_names)),
    )
    return preset_buttons, refresh_button


@app.cell(hide_code=True)
def _(explorer_names, explorer_notions, get_drawn, kit, map_controls, mo, preset_buttons, refresh_button):
    _current = kit.settings_from(map_controls.value, explorer_names)
    kit.controls_layout(
        mo, map_controls, mo.hstack(list(preset_buttons), justify="start", gap=0.5), refresh_button,
        kit.refresh_status(mo, _current, get_drawn()), show_case_notion=len(explorer_notions) > 1,
    )
    return


@app.cell(hide_code=True)
def _(event_log, get_drawn, kit, mo, panel, record, resume):
    _settings = get_drawn()
    mo.stop(_settings is None, mo.md("*Choose the settings, then press Refresh visualization.*"))
    _problems = kit.fold_problems(_settings)
    mo.stop(bool(_problems), mo.callout(mo.md("  \n".join(_problems)), kind="danger"))
    mo.stop(_settings["activities"] == [], mo.callout(mo.md("Select at least one activity."), kind="warn"))
    # every map you ask for is a new step, even when it repeats an earlier one
    _args = (
        event_log, _settings["activities"], _settings["map_type"], _settings["allow_loops"],
        _settings["show_empty"], _settings["folds"], _settings["case_notion"], 620,
    )
    try:
        if resume["settings"] is not None and kit.normalise_settings(_settings) == resume["settings"]:
            resume["settings"] = None  # the map of the stored history, shown again: not a new step
            map_figure, map_meta = kit.draw_map(*_args)
        else:
            resume["settings"] = None
            map_figure, map_meta = record(["map_figure", "map_meta"], kit.draw_map, *_args, name="draw_map", replay_stored=False)
            panel.refresh()  # so that the side panel knows the new step before the first annotation is written on it
    except ValueError as _error:
        mo.stop(True, mo.callout(mo.md(str(_error)), kind="danger"))
    return map_figure, map_meta


@app.cell(hide_code=True)
def _(kit, map_figure, map_meta, mo, show_chart, state_of):
    mo.vstack([
        mo.md(kit.describe_settings(map_meta["settings"])),
        mo.md(kit.describe_map(map_meta)),
        mo.callout(
            mo.md(f"Not in this log under this case notion, so not drawn: {', '.join(f'`{a}`' for a in map_meta['left_out'])}."),
            kind="neutral",
        ) if map_meta["left_out"] else mo.md(""),
        mo.callout(
            mo.md(f"This map has **{map_meta['total_nodes']:,} nodes**; select fewer activities or another abstraction for a readable map."),
            kind="warn",
        ) if map_meta["total_nodes"] > 1000 else mo.md(""),
        show_chart(mo.as_html(map_figure), artifact_id=state_of("map_figure"), artifact_name="process_map", figure=map_figure),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Your annotations

    Your annotations are your answers, and each annotation is attached to the table or map it is about:

    1. In the side panel, press **Pick** and click the table or the map (or a part of it) that the annotation is about.
    2. Write the annotation and add **tags**, separated by spaces: the kind of the annotation (`intent` or `finding`) and the task it belongs
       to (`task8`, `task9` or `task10`), for example `finding task8`.
    3. Press **Add**.

    Write two kinds of annotations, as in the tutorial:

    - An **intent** carries the tag `intent` and states what a map is for and why you chose its settings. Write it right after the
      map appears.
    - A **finding** carries the tag `finding` and states what the map shows, with the numbers that support it (from the tooltips),
      and what it means for the process.

    Each map you draw stays a step of your analysis, and your annotations stay attached to the step they were written on, so you can
    draw a new map at any time without losing earlier annotations.
    """)
    return


if __name__ == "__main__":
    app.run()
