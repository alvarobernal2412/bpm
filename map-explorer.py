# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.2",
#     "pmprov[duckdb,parquet,graph]>=0.10.0",
#     "marimo-pmprov[pdf]>=0.11.1",
#     "pandas>=3.1.0",
#     "pyarrow>=15",
#     "altair>=5.5",
#     "vegafusion>=2.0",
#     "pytz",
#     "linear-continuous-process-mapper>=0.1.0",
#     "plotly>=7.1.0",
#     "kaleido>=1.0.0",
#     "networkx>=3.7",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Map explorer

    Your work is saved automatically. You can close this page and continue later with the same key. If marimo shows a message that something failed, or the page stops responding, reload the page: your work comes back as you left it.
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
    from provenance_widget.display import show_chart, show_table
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
        ak,
        describe_run,
        du,
        init_marimo,
        kit,
        mo,
        pd,
        project_file,
        relocate_artifacts,
        show_chart,
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
        PROVENANCE_DIR = ak.session_folder(_key, ak.MAP_EXPLORER_NOTEBOOK)
        sync = Sync(ak.sync_url(SYNC_URL, ak.MAP_EXPLORER_NOTEBOOK), _key, PROVENANCE_DIR)
        sync.restore()
        mo.stop(sync.status.state == "unauthorized", mo.callout(mo.md(sync.status.message), kind="danger"))
    else:
        PROVENANCE_DIR = Path(kit.os.environ.get("PMPROV_DIR") or HERE / "provenance")
    (PROVENANCE_DIR / "artifacts").mkdir(parents=True, exist_ok=True)
    # which notebook this is, and a hash of its file: saved with the work, so the course server knows what version made it
    _info_file = ak.write_notebook_info(PROVENANCE_DIR, ak.MAP_EXPLORER_NOTEBOOK, globals().get("__file__"))  # kept, so it is not shown
    return PROVENANCE_DIR, sync


@app.cell(hide_code=True)
def _(PROVENANCE_DIR, ak, init_marimo, kit, relocate_artifacts):
    # a history that was downloaded from another machine points at that machine's folders
    relocate_artifacts(PROVENANCE_DIR / "provenance.db", PROVENANCE_DIR / "artifacts")
    rt = init_marimo(
        history_name=ak.MAP_EXPLORER_HISTORY_NAME,
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
        empty_hint=(
            "No annotations yet. Press Anchor, click the map (or a node or link of it) the annotation is about, write it with tags "
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
def _(ak, mo, project_file, record):
    # Load the event log; the step records the name of the file, not a folder of somebody's computer
    def load_event_log(name):
        return ak.load_event_log(project_file(name))

    event_log = record(["event_log"], load_event_log, ak.DHANA)
    mo.md(f"**{len(event_log):,}** events loaded.")
    return (event_log,)


@app.cell(hide_code=True)
def _(ak, kit, event_log):
    # The activities do not depend on what a path is, so choosing another attribute changes nothing until Refresh is pressed.
    explorer_names = sorted(event_log[ak.ACTIVITY].unique())
    # "Each path is": the attributes whose values can make up a path; the case id is the normal one
    explorer_notions = {("Case ID" if c == ak.CASE_ID else c): c for c in ak.path_attribute_options(event_log)}
    return explorer_names, explorer_notions


@app.cell(hide_code=True)
def _(adapter, ak, event_log, explorer_names, explorer_notions, kit, mo):
    # draft: what the controls are built from; drawn: what the map shows (changed by Refresh). The explorer starts on the 5 most frequent
    # activities (all 25 make a map of 342 nodes that takes ten seconds to draw and is slow to render in the browser) or
    # as the analyst left it (including what each path was).
    _column = (ak.params_at(adapter, None, "to_lcm_log") or {}).get("case_column")
    _settings = kit.normalise_settings(
        {**(kit.last_map_settings(adapter) or {"activities": sorted(event_log[ak.ACTIVITY].value_counts().index[:5])}), "case_notion": _column if _column in explorer_notions.values() else ak.CASE_ID}
    )
    get_draft, set_draft = mo.state(_settings)
    get_drawn, set_drawn = mo.state(_settings)
    return get_draft, get_drawn, set_draft, set_drawn


@app.cell(hide_code=True)
def _(explorer_names, explorer_notions, get_draft, kit, mo):
    map_controls = kit.map_controls(mo, explorer_names, get_draft() or {"activities": []}, explorer_notions)
    return (map_controls,)


@app.cell(hide_code=True)
def _(explorer_names, kit, map_controls, mo, set_drawn):
    refresh_button = mo.ui.button(
        label="Refresh visualization", kind="success",
        on_click=lambda _: set_drawn(kit.settings_from(map_controls.value, explorer_names)),
    )
    return (refresh_button,)


@app.cell(hide_code=True)
def _(explorer_names, explorer_notions, get_drawn, kit, map_controls, mo, refresh_button):
    _current = kit.settings_from(map_controls.value, explorer_names)
    kit.controls_layout(
        mo, map_controls, mo.md(""), refresh_button,
        kit.refresh_status(mo, _current, get_drawn()), show_case_notion=len(explorer_notions) > 1,
    )
    return


@app.cell(hide_code=True)
def _(ak, get_drawn, kit, event_log, mo, panel, record):
    _settings = get_drawn()
    mo.stop(_settings is None, mo.md("*Choose the settings, then press Refresh visualization.*"))
    _problems = kit.fold_problems(_settings)
    mo.stop(bool(_problems), mo.callout(mo.md("  \n".join(_problems)), kind="danger"))
    mo.stop(_settings["activities"] == [], mo.callout(mo.md("Select at least one activity."), kind="warn"))
    path_column = _settings["case_notion"]  # "Each path is": the attribute whose values make up a path
    try:
        # every map you ask for is a recorded step: first the log with that attribute as the case, then the map of it
        lcm_log = record(["lcm_log"], ak.to_lcm_log, event_log, path_column)
        map_figure, map_meta = record(
            ["map_figure", "map_meta"], kit.draw_map,
            lcm_log, _settings["activities"], _settings["map_type"], _settings["allow_loops"],
            _settings["show_empty"], _settings["folds"], "application", 620,  # the log's own case column is now the chosen attribute
        )
        panel.refresh()  # so that the side panel knows the new step before the first annotation is written on it
    except ValueError as _error:
        _available = ", ".join(f"`{a}`" for a in sorted(lcm_log["concept:name"].unique()))
        mo.stop(True, mo.callout(mo.md(f"{_error} The activities that occur when each path is `{path_column}` are: {_available}."), kind="danger"))
    return map_figure, map_meta, path_column


@app.cell(hide_code=True)
def _(ak, kit, map_figure, map_meta, mo, path_column, show_chart, state_of):
    mo.vstack([
        mo.md(kit.describe_settings(map_meta["settings"])),
        mo.md(f"**Each path is:** `{path_column}`" if path_column != ak.CASE_ID else ""),
        mo.md(kit.describe_map(map_meta)),
        mo.callout(
            mo.md(f"No event of these has a value for the attribute that makes up a path, so not drawn: {', '.join(f'`{a}`' for a in map_meta['left_out'])}."),
            kind="neutral",
        ) if map_meta["left_out"] else mo.md(""),
        show_chart(mo.as_html(map_figure), artifact_id=state_of("map_figure"), artifact_name="process_map", figure=map_figure),
    ])
    return


if __name__ == "__main__":
    app.run()
