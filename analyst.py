# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.2",
#     "pmprov[duckdb,parquet,graph]>=0.10.0",
#     "marimo-pmprov[pdf]>=0.2.4",
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
    # BPI Challenge 2017, Task 1: Schemas (analyst)

    The analyst notebook. It answers the three questions of the first exploratory task on the **whole** log
    (31,509 applications, 1.2 million events) with the maps of the
    [Linear Continuous Process Mapper](https://github.com/aaronkurz/linear-continuous-process-mapper-marimo), and records
    every analysis step with `pmprov`. In the sidebar you can **Pick** a map or a table as the target of a note, write
    the note, and **Export PDF** for the report. The recorded steps and notes are stored in the `provenance/` folder
    next to this notebook; open `reviewer.py` to step through them read-only.

    1. Which data schema is associated with the activity `A_Create Application`?
    2. Which attributes of this schema have missing values?
    3. Does the log have any attribute that is re-used across different activities?

    A map shows the order of activities, not attributes. To use it for an attribute question, the log is first reduced
    to the events that carry the attribute: the activities in such a map are exactly the activities that carry it.
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
    import os as _os
    import sys as _sys
    import tempfile as _tempfile
    from pathlib import Path

    import warnings as _warnings

    from tracker import init_marimo
    from provenance_widget.pmprov_adapter import PmprovAdapter
    from provenance_widget.widget import ProvenancePanel
    from provenance_widget.display import show_chart, show_table

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

    # The Linear Continuous Process Mapper (its `app` and `core` packages) is vendored in ./lcm
    if str(HERE / "lcm") not in _sys.path:
        _sys.path.insert(0, str(HERE / "lcm"))

    # Where the provenance is stored: ./provenance next to the notebooks, or PMPROV_DIR. If that folder cannot be
    # written (read-only project), a temporary folder is used so the notebook still runs.
    _wanted = Path(_os.environ.get("PMPROV_DIR") or HERE / "provenance")
    try:
        (_wanted / "artifacts").mkdir(parents=True, exist_ok=True)
        PROVENANCE_DIR = _wanted
    except OSError:
        PROVENANCE_DIR = Path(_tempfile.mkdtemp(prefix="bpm-provenance-"))
        (PROVENANCE_DIR / "artifacts").mkdir(parents=True, exist_ok=True)

    def relocate_artifacts(db_path, artifact_dir):
        """Point the stored artifacts at `artifact_dir`.

        pmprov stores the absolute path of every artifact file, so a provenance folder that was copied or downloaded
        (from molab to a laptop, say) still points at its old location, and its maps and tables could not be restored.
        The files are found again by name in the folder next to the database.
        """
        if not Path(db_path).exists():
            return 0
        import re

        import duckdb

        try:
            con = duckdb.connect(str(db_path))
            try:
                changed = 0
                rows = con.execute("SELECT artifact_state_id, content_ref FROM artifact_states").fetchall()
                for artifact_state_id, ref in rows:
                    new = str(Path(artifact_dir) / re.split(r"[\\/]", ref)[-1])
                    if new != ref:
                        con.execute(
                            "UPDATE artifact_states SET content_ref = ? WHERE artifact_state_id = ?",
                            [new, artifact_state_id],
                        )
                        changed += 1
                return changed
            finally:
                con.close()
        except Exception:
            return 0  # no history stored yet

    # a history that was downloaded from another machine points at that machine's folders
    relocate_artifacts(PROVENANCE_DIR / "provenance.db", PROVENANCE_DIR / "artifacts")

    HISTORY_NAME = "BPI 2017 Task 1 with LCM maps"

    # pmprov warns that its cell rewriting is not active; the steps are recorded explicitly with record() below
    _warnings.filterwarnings("ignore", message=r"init_marimo\(\) was called but patch_marimo_ast_compile")

    rt = init_marimo(
        history_name=HISTORY_NAME,
        branch_name="main",
        db_path=str(PROVENANCE_DIR / "provenance.db"),
        artifact_dir=str(PROVENANCE_DIR / "artifacts"),
        fresh=False,  # continue the stored history of this name after a restart
    )

    def record(targets, function, *args, name=None, **kwargs):
        """Run one analysis step and record it with pmprov.

        pmprov normally records a notebook by rewriting its cells, which needs marimo to be started with a patch.
        A platform such as molab starts marimo itself, so the steps are recorded explicitly instead: this runs
        `function(*args, **kwargs)`, stores its inputs and the outputs under the names in `targets`, and returns the
        result unchanged.
        """
        label = name or function.__name__
        return rt.trace_step(
            func=function,
            func_name=label,
            raw_line=f"{', '.join(targets)} = {label}(...)",
            args=list(args),
            kwargs=kwargs,
            targets=list(targets),
        )

    return (
        HERE,
        PROVENANCE_DIR,
        Path,
        PmprovAdapter,
        ProvenancePanel,
        mo,
        pd,
        record,
        rt,
        show_chart,
        show_table,
    )


@app.cell(hide_code=True)
def _(PROVENANCE_DIR, mo):
    mo.callout(mo.md(f"Provenance is stored in `{PROVENANCE_DIR}`."), kind="info")
    return


@app.cell(hide_code=True)
def _(PmprovAdapter, ProvenancePanel, rt):
    adapter = PmprovAdapter(rt)
    # the analyst can annotate, edit and export; the reviewer notebook opens the same store read-only
    panel = ProvenancePanel(source=adapter, mode="analyst", tabs=["curated"])
    return (panel,)


@app.cell(hide_code=True)
def _(mo, panel):
    # mo.sidebar(...) has to be the last bare expression of its cell to render
    mo.sidebar(panel.sidebar())
    return


@app.cell(hide_code=True)
def _(HERE, Path, pd, record):
    from app.factory import create_process_analytics_service

    ACTIVITY = "concept:name"
    CASE_ID = "case:concept:name"
    TIMESTAMP = "time:timestamp"

    def load_event_log(parquet_path):
        """The BPI 2017 log as a DataFrame (Parquet copy of BPI_Challenge_2017.xes, all 19 columns)."""
        if not Path(parquet_path).exists():
            raise FileNotFoundError(
                f"{parquet_path} is missing. Put the Parquet copy of the log in the data folder next to the notebook."
            )
        return pd.read_parquet(parquet_path)

    event_log = record(["event_log"], load_event_log, HERE / "data" / "bpi2017.parquet")
    return ACTIVITY, CASE_ID, TIMESTAMP, create_process_analytics_service, event_log


@app.cell(hide_code=True)
def _(ACTIVITY, CASE_ID, event_log, mo):
    mo.md(f"""
    **The log:** {event_log[CASE_ID].nunique():,} applications, {len(event_log):,} events,
    {event_log[ACTIVITY].nunique()} activities, {event_log.shape[1]} columns. This is the full log, not the smaller one.
    """)
    return


@app.cell(hide_code=True)
def _(ACTIVITY, CASE_ID, TIMESTAMP, create_process_analytics_service, pd):
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
        service = create_process_analytics_service(log)
        figure, metadata = service.generate_sankey_figure(
            selected_activities=activities,
            builder_key=builder,
            merge_threshold=None,
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
def _(create_schema, mo, panel, show_table):
    _state = panel.latest_state_id or "analysis"
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
    return application_figure, application_meta, start_share


@app.cell(hide_code=True)
def _(CASE_ID, application_figure, application_meta, event_log, mo, panel, show_chart, start_share):
    _state = panel.latest_state_id or "analysis"
    mo.vstack([
        mo.md(
            f"**Set-based map of the application states, all {event_log[CASE_ID].nunique():,} cases.** "
            f"{start_share:.1f}% of the cases start with `A_Create Application`, so its schema is the one every case "
            f"enters the process with. The map has {application_meta['total_nodes']} nodes, "
            f"{application_meta['terminal_nodes']} of them where cases end."
        ),
        show_chart(
            mo.as_html(application_figure),
            artifact_id=_state,
            artifact_name="map_application_states",
            figure=application_figure,
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
def _(missing_values, mo, outside_schema, panel, show_table):
    _state = panel.latest_state_id or "analysis"
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
def _(attribute_reuse, mo, panel, show_table):
    _state = panel.latest_state_id or "analysis"
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
def _(mo, offer_id_activities, offer_id_figure, offer_id_meta, panel, show_chart):
    _state = panel.latest_state_id or "analysis"
    mo.vstack([
        mo.md(
            f"**`OfferID` is re-used.** The map of the events that carry it has {len(offer_id_activities)} activities: "
            f"{', '.join(offer_id_activities)}. {offer_id_meta['total_nodes']} nodes."
        ),
        show_chart(
            mo.as_html(offer_id_figure),
            artifact_id=_state,
            artifact_name="map_offer_id_carriers",
            figure=offer_id_figure,
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
def _(credit_score_activities, credit_score_figure, mo, panel, show_chart):
    _state = panel.latest_state_id or "analysis"
    mo.vstack([
        mo.md(
            f"**`CreditScore` is not re-used.** The map of the events that carry it has "
            f"{len(credit_score_activities)} activity: {', '.join(credit_score_activities)}."
        ),
        show_chart(
            mo.as_html(credit_score_figure),
            artifact_id=_state,
            artifact_name="map_credit_score_carriers",
            figure=credit_score_figure,
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
def _(distinct_activities, event_log, mo):
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

    explorer_log = record(["explorer_log"], case_activity_timestamp, event_log)
    explorer_figure, explorer_meta = record(
        ["explorer_figure", "explorer_meta"],
        draw_map, explorer_log, _view["activities"], _view["builder"], _view["loops"], _view["empty"], 650,
        name="draw_explorer_map",
    )
    mo.as_html(explorer_figure)
    return


if __name__ == "__main__":
    app.run()
