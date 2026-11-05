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
    # Tutorial: reading and annotating linear continuous process maps

    This notebook prepares you for the process map questions of the assignment. It has three parts:

    1. **A recorded analysis**, replayed step by step from the side panel. It was made with the same map explorer that you will
       use in the student notebook, on one part of the BPI Challenge 2017 loan application log: its **workflow
       activities** (`W_`), the work that bank employees do on an application. The tasks ask about other parts of the log (the
       application and offer lifecycles and the outcomes), so this analysis shows *how to read maps*, not what the tasks find.
    2. **A reference** of the elements of a map, of the map settings and of the patterns that the maps make visible.
    3. **A map explorer** at the end of the page, where you change the settings yourself and draw your own maps of the log.

    **How to use the side panel**

    - The arrows at the top of the panel (**First**, **Back**, **Next**, **Latest**) move through the recorded analysis one step
      at a time. Every recorded table and map on this page shows its content *as it was at that step*; a section whose step has not
      happened yet stays empty.
    - Each annotation in the panel has a **Replay** button: it moves the analysis to the step the annotation was written on and highlights the
      table or map the annotation refers to.
    - Nothing on this page is recorded, and the annotations cannot be changed here. You write your own annotations in the student notebook.

    **The data.** *BPI Challenge 2017* (van Dongen, B.F., 4TU.ResearchData,
    [doi:10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b](https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b)): the
    loan applications that a Dutch financial institution received in 2016.
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

    # The course server keeps the recorded tutorial under a read key whose course is closed. Without a key, or when the server does
    # not answer, the copy in the repository (histories/tutorial.zip) is replayed.
    SYNC_URL = _os.environ.get("PMPROV_SYNC_URL", "https://provenance.alvispace.com")
    TUTORIAL_KEY = _os.environ.get("BPM_TUTORIAL_KEY", "tutorial-tutorial-wm4cgp5w")  # read key: its course is closed, so it cannot overwrite
    return PmprovAdapter, ProvenancePanel, SYNC_URL, TUTORIAL_KEY, kit, mo, show_chart, show_table


@app.cell(hide_code=True)
def _(SYNC_URL, TUTORIAL_KEY, kit, mo):
    rt, recorded_source = kit.open_recorded_analysis(kit.TUTORIAL_ZIP, SYNC_URL, TUTORIAL_KEY, kit.TUTORIAL_HISTORY_NAME)
    mo.stop(
        rt is None,
        mo.callout(mo.md(f"The recorded tutorial could not be loaded ({recorded_source}). Run the notebook again."), kind="danger"),
    )
    return recorded_source, rt


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
def _(mo, recorded_source, snap):
    mo.callout(mo.md(f"{snap.banner()}  \nThe recorded analysis was read from {recorded_source}."), kind="info")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. The event log

    The first recorded steps load the log and count its activities. The table lists every activity with the number of events it
    has, the number of applications (cases) in which it occurs and that number as a share of all applications.
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
    ## 2. The elements of a map

    A linear continuous process map draws **every case as a path from left to right**. Cases that start in the same way share a
    band; the **width of a band is proportional to the number of cases** that follow it, so the widths at every node add up
    exactly to the cases that pass through it. No case is hidden and no band is drawn that no case follows.

    | Element | What it shows |
    |---|---|
    | White node on the left | The start: all cases (paths) of the map. |
    | Band | The cases that perform the next activity; its color is the activity (see the legend on the right). |
    | Light gray node | A point that every case passes through and leaves again. |
    | Dark gray or black node | A point where some cases (dark gray) or many cases (black) **end**. Ending cases are called *leakage*. |
    | `EMPTY TRACE` node | The cases that contain none of the selected activities. |
    | Loop on a node (self-loop) | An activity that does not move the case to a new node, for example an activity that is repeated. |
    | Tooltip (hover) | The number of cases flowing in and out of a node, and its leakage. |

    You can **drag a node** to untangle the bands; this changes the drawing only, not the numbers.

    **Events, not pieces of work.** A map counts events. In this log a `W_` activity is a piece of work done by an employee, and one
    piece of work leaves several events under the same name (scheduled, started, suspended, resumed, completed). A self-loop on a
    `W_` activity, or a count of its events, therefore does not by itself say that the work was repeated. Keep this in mind when you
    read the recorded maps below.
    """)
    return


@app.cell(hide_code=True)
def _(kit, mo):
    def _setting(title, text, figure):
        return mo.vstack([mo.md(f"### {title}\n\n{text}"), kit.settings_figure(mo, figure)], gap=0.5)

    mo.vstack([
        mo.md(r"""
        ## 3. The settings of a map

        These are the settings of the map explorer at the end of the page. In each figure the red box marks the control that changes
        the setting, and the maps below it are the same log drawn with different values of it.
        """),
        _setting(
            "Abstraction",
            "What a node stands for. **Set-based:** the *set* of activities a case has done so far, whatever their order; different "
            "orders of the same activities meet in one node and a repeated activity is a self-loop. **Last-activity-based:** the "
            "*last* activity a case has done; this is the directly-follows graph, the smallest map, but a cycle can mean a repetition "
            "or only a different order. **Sequence-based:** the exact *sequence* so far; this is the prefix tree of the log, nothing "
            "is merged, so it is precise but can be very large.",
            "settings-abstraction.png",
        ),
        _setting(
            "Activities to draw",
            "Only the selected activities are kept in every path; the others are removed. Selecting the states of one business "
            "object (an application, an offer) is the most effective way to make a map readable. The **quick-selection buttons** "
            "select a whole family of activities.",
            "settings-activities.png",
        ),
        _setting(
            "Activity folding",
            "Several activities are drawn as one, under a name you choose (for example all rejections as *Rejected*). A fold is "
            "drawn when at least one of its activities is selected, and an activity can be in one fold only.",
            "settings-folding.png",
        ),
        _setting(
            "Show self-loops",
            "Whether activities that do not move a case to a new node are drawn as loops. Hidden, the map shows only how the cases "
            "move on.",
            "settings-loops.png",
        ),
        _setting(
            "Show empty traces",
            "Whether the cases with none of the selected activities are drawn as an `EMPTY TRACE` node. With few activities selected "
            "this is most of the log, which is why the map shows it by default.",
            "settings-empty.png",
        ),
        _setting(
            "Each path is",
            "What a path stands for: a loan application, or one offer (the offer events grouped by `OfferID`). The recorded analysis "
            "on this page does not use it; the tasks do.",
            "settings-notion.png",
        ),
        mo.md(r"""
        A map is drawn only when you press **Refresh visualization**; the line next to the button tells you whether the map on screen
        matches the settings above it.
        """),
    ], gap=1.5)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Patterns to look for

    The recorded analysis demonstrates mainstream vs. exceptional behavior, leakage, rework, folding and sequential variants, and
    compares the abstractions; its annotations are tagged with the name of the pattern. The other patterns (knockout structure, unexpected
    ordering, outcome distribution) are for you to look for in the tasks.

    | Pattern | How it appears in a map | Settings that show it best |
    |---|---|---|
    | **Mainstream vs. exceptional behavior** | A sequence of thick bands, next to thin bands that branch off. | Set-based, with the activities of one business object. |
    | **Knockout structure** | A sequence of stages, each of which lets some cases leave the process (a decline, a cancellation). | Last-activity-based. |
    | **Leakage** | Dark gray or black nodes where you did not expect cases to end. | Set-based or last-activity-based; the tooltip gives the number. |
    | **Alternative or unexpected ordering** | Several bands that lead into the same node from different directions. | Set-based (the last-activity map shows them as cycles). |
    | **Rework** | A self-loop: the same activity repeated within a case. | Set-based; sequence-based on few activities to count the repetitions. |
    | **Outcome distribution** | The widths of the bands into the activities that end a case, plus the `EMPTY TRACE` node for cases without an outcome. | Only the outcome activities selected, empty traces shown. |
    | **Sequential variants** | The leaves of the prefix tree: one per distinct sequence. | Sequence-based, with few activities. |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. The recorded maps

    This cell shows the map of the step the side panel is on, with the settings that drew it. Move through the steps to see the
    maps of the recorded analysis one after another. **Open in the map explorer** copies the settings of the map into the map
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
    ## 6. Writing intents and findings

    In the student notebook the side panel has a composer for annotations. Your annotations are what you hand in, so each annotation should be
    attached to the table or map it is about:

    1. Press **Pick** and click the table or the map (or a part of it) that the annotation is about.
    2. Write the annotation and add **tags** (separated by spaces), starting with the kind of the annotation (see below).
    3. Press **Add**. The annotation is attached to the step that produced the table or map, and it can be replayed from there.

    The recorded analysis on this page uses two kinds of annotations, and you should use them in the same way:

    - An **intent** carries the tag `intent` and states what a map is for: the question it should answer and why you chose its
      settings. Write it right after the map appears, before the findings.
    - A **finding** carries the tag `finding` and states what the map shows, with the numbers that support it (read them from the
      tooltips) and what they mean for the process.

    An annotation can have more tags, to group it: here the pattern it shows (`rework`, `leakage`, ...); in your own annotations the task it
    answers (`task8`, `task9` or `task10`). The tags of an annotation belong to that annotation, so an intent and the findings written on the same
    map each show their own.

    Step through the annotations in the side panel and compare each intent with the settings of its map, and each finding with the map.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. Map explorer

    Draw your own maps of the BPI 2017 log. It opens on the workflow activities; drawing all 26 takes several seconds. Choose the settings and press **Refresh visualization**. The maps drawn here are
    not recorded.
    """)
    return


@app.cell(hide_code=True)
def _(kit):
    # the explorer works on the live log, loaded once
    explorer_log = kit.load_event_log(kit.BPI2017)
    explorer_names = kit.distinct_activities(explorer_log)
    explorer_notions = kit.case_notions_of(explorer_log)
    # the explorer opens on the workflow activities; drawing all 26 is slow
    explorer_start = {"activities": [a for a in explorer_names if a.startswith("W_")]}
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
