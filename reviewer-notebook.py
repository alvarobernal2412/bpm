# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.2",
#     "pmprov[duckdb,parquet,graph]>=0.10.0",
#     "marimo-pmprov[pdf]>=0.4.5",
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
    # Reviewer notebook: a student's Tasks 8, 9 and 10

    This notebook shows the work of one student in the **student notebook**, as a reviewer. Paste the student's key below. The
    analysis, the tables and maps they produced and the notes they wrote (intents and findings) are then replayed here. Nothing
    you do on this page changes the student's work: it is only read.

    **The tasks the student answered**

    - **Task 8.** Keep only the Loan Application lifecycle (all activities starting with `A_`) in the process map and write down at
      least three interesting observations.
    - **Task 9.** Repeat Task 8 for the Offer lifecycle: keep the activities starting with `O_`, but not `O_Create Offer`.
    - **Task 10.** Create a visualization of the case outcome distribution of the log. The set of outcomes must be pairwise
      mutually exclusive and complete. Briefly reflect on the result.

    **How to use the side panel**

    - The arrows at the top of the panel (**First**, **Back**, **Next**, **Latest**) move through the analysis one step at a time.
      Every recorded table and map on this page shows its content *as it was at that step*.
    - **Replay** on a note moves the analysis to the step the note was written on and highlights the table or map it refers to.
    - Notes are tagged with their kind (`intent`, `finding`) and the task they answer (`task8`, `task9`, `task10`).
    - The **map explorer** at the end of the page draws maps with any settings, to check a finding. Nothing drawn there is
      recorded, and **Open in the map explorer** below a recorded map copies its settings there.
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
    from pathlib import Path

    from provenance_widget.pmprov_adapter import PmprovAdapter
    from provenance_widget.widget import ProvenancePanel
    from provenance_widget.display import show_chart, show_table
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

    # The course server that keeps each student's work. A reviewer only reads it: nothing here ever saves.
    SYNC_URL = _os.environ.get("PMPROV_SYNC_URL", "https://provenance.alvispace.com")
    return PmprovAdapter, ProvenancePanel, Path, SYNC_URL, Sync, kit, mo, show_chart, show_table


@app.cell(hide_code=True)
def _(kit, mo):
    key_box = mo.ui.anywidget(
        kit.KeyBox(store="bpm-reviewer-key", placeholder="Paste the student's key here")
    )
    mo.vstack([mo.md("### The student's key"), key_box])
    return (key_box,)


@app.cell(hide_code=True)
def _(SYNC_URL, Path, Sync, key_box, kit, mo):
    # The student's work is copied into a fresh folder and opened there, without a Sync that saves: a reviewer cannot change it.
    mo.stop(not SYNC_URL, mo.callout(mo.md("This notebook needs the course server (`PMPROV_SYNC_URL`)."), kind="danger"))
    _key = (key_box.value.get("key") or "").strip()
    mo.stop(not _key, mo.callout(mo.md("Paste the student's key above to start."), kind="info"))
    folder = Path(kit.tempfile.mkdtemp(prefix="bpm-review-")) / "provenance"
    _sync = Sync(SYNC_URL, _key, folder)
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
    rt = kit.open_recorded(folder, kit.HISTORY_NAME)
    mo.stop(
        rt is None,
        mo.callout(
            mo.md(f"The work saved under this key has no analysis named '{kit.HISTORY_NAME}'. Is it the key of the student notebook?"),
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
    snap = panel.snapshot(get_cursor() or adapter.latest_state_id())
    record, state_of = kit.reviewer_recorder(snap, mo)
    return record, snap, state_of


@app.cell(hide_code=True)
def _(mo, snap):
    mo.callout(mo.md(f"{snap.banner()}  \nThis is the student's saved work, read from the course server. It cannot be changed here."), kind="info")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. The event log

    The first steps load the log and count its activities. The table lists every activity with its family (`A_`, `O_`
    or `W_`), the number of events it has, the number of applications (cases) in which it occurs and that number as a share of all
    applications.
    """)
    return


@app.cell(hide_code=True)
def _(kit, mo, record, show_table, state_of):
    log_summary = record(["log_summary"], kit.summarise_log, None)
    activities = record(["activities"], kit.activity_overview, None)
    mo.vstack([
        mo.md(
            f"**The log:** {log_summary['cases']:,} cases, {log_summary['events']:,} events, "
            f"{log_summary['activities']} activities."
        ),
        show_table(
            mo.ui.table(activities, selection=None, pagination=None),
            artifact_id=state_of("activities"),
            artifact_name="activity_overview",
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. The recorded maps

    This cell shows the map of the step the side panel is on, with the settings that drew it. Move through the steps to see the
    maps the student drew one after another. **Open in the map explorer** copies the settings of the map into the map
    explorer at the end of the page and draws it there, so that you can change them and compare.
    """)
    return


@app.cell(hide_code=True)
def _(kit, record):
    # the arguments are ignored here: record() returns what the recorded step drew
    map_figure, map_meta = record(
        ["map_figure", "map_meta"], kit.draw_map, None, None, None, None, None, None, None, name="draw_map"
    )
    return map_figure, map_meta


@app.cell(hide_code=True)
def _(kit, map_meta, mo, set_draft, set_drawn):
    _settings = map_meta.get("settings") if isinstance(map_meta, dict) else None

    def _open(_):
        set_draft(_settings)
        set_drawn(kit.normalise_settings(_settings))

    open_in_explorer = mo.ui.button(label="Open in the map explorer", on_click=_open, disabled=_settings is None)
    return (open_in_explorer,)


@app.cell(hide_code=True)
def _(kit, map_figure, map_meta, mo, open_in_explorer, show_chart, state_of):
    mo.vstack([
        mo.md(kit.describe_settings(map_meta["settings"]) if isinstance(map_meta, dict) else ""),
        mo.md(kit.describe_map(map_meta)),
        show_chart(mo.as_html(map_figure), artifact_id=state_of("map_figure"), artifact_name="process_map"),
        open_in_explorer,
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Map explorer

    Draw your own maps of the BPI 2017 log. Choose the settings and press **Refresh visualization**. The maps drawn here are not
    recorded. Maps with many activities (all of them, or the workflow activities) take several seconds to draw.
    """)
    return


@app.cell(hide_code=True)
def _(kit):
    # the explorer works on the live log, loaded once
    explorer_log = kit.load_event_log(kit.BPI2017)
    explorer_names = kit.distinct_activities(explorer_log)
    explorer_notions = kit.case_notions_of(explorer_log)
    # the explorer opens on the application states; drawing all 26 activities is slow
    explorer_start = {"activities": [a for a in explorer_names if a.startswith("A_")]}
    return explorer_log, explorer_names, explorer_notions, explorer_start


@app.cell(hide_code=True)
def _(mo):
    # draft: what the controls are built from; drawn: what the map shows (changed by Refresh or by "Open in the map explorer")
    get_draft, set_draft = mo.state(None)
    get_drawn, set_drawn = mo.state(None)
    return get_draft, get_drawn, set_draft, set_drawn


@app.cell(hide_code=True)
def _(explorer_names, explorer_notions, explorer_start, get_draft, kit, mo):
    map_controls = kit.map_controls(mo, explorer_names, get_draft() or explorer_start, explorer_notions)
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
def _(explorer_log, get_drawn, kit, mo):
    _settings = get_drawn()
    mo.stop(_settings is None, mo.md("*Choose the settings, then press Refresh visualization.*"))
    _problems = kit.fold_problems(_settings)
    mo.stop(bool(_problems), mo.callout(mo.md("  \n".join(_problems)), kind="danger"))
    try:
        _figure, _meta = kit.draw(explorer_log, _settings)
    except ValueError as _error:
        mo.stop(True, mo.callout(mo.md(str(_error)), kind="danger"))
    mo.vstack([
        mo.md(kit.describe_map(_meta)),
        mo.callout(
            mo.md(f"Not in this log under this case notion, so not drawn: {', '.join(f'`{a}`' for a in _meta['left_out'])}."),
            kind="neutral",
        ) if _meta["left_out"] else mo.md(""),
        _figure,
    ])
    return


if __name__ == "__main__":
    app.run()
