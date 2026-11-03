"""Record the model analysis of Task 1 and write it to data/model-solution/provenance.zip, which model-solution.py replays.

    uv run --python 3.13 --with marimo --with "pmprov[duckdb,parquet,graph]>=0.10" --with "marimo-pmprov[pdf]>=0.4.2" \\
        --with linear-continuous-process-mapper --with plotly --with kaleido --with networkx --with pandas \\
        python tools/make_model_solution.py

It runs the steps through the same `record()` the student notebook uses (bpm_kit.analyst_recorder), so the history is the one a
student would produce, and then writes the notes: each one attached to the table or the map that answers the question, with a
title, a text and tags, the way the annotated examples of the course do. Run it again after a change to the analysis or to a
note; model-solution.py needs no change unless a step was added or renamed.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402
import bpm_kit as kit  # noqa: E402
import tracker.runtime as _tracker_runtime  # noqa: E402
from provenance_widget.pmprov_adapter import PmprovAdapter  # noqa: E402
from provenance_widget.portable import zip_provenance  # noqa: E402
from tracker.runtime import RuntimeTracker  # noqa: E402
from tracker.storage import DuckDBSQLiteBackend, _connect_lock  # noqa: E402

OUTPUT = ROOT / "data" / "model-solution" / "provenance.zip"
AUTHOR = "Model solution"
PORTABLE_STORAGE_VERSION = "v1.0.0"  # the oldest DuckDB file format: read by every DuckDB from 1.0 on

# one colour per kind of note, so the sidebar can be read at a glance
COLORS = {"first look": "#64748B", "1a": "#0EA5E9", "1b": "#F59E0B", "1c": "#10B981", "finding": "#A855F7"}


def tags(*names):
    return [{"name": name, "color": COLORS[name]} for name in names]


def main(output: Path = OUTPUT) -> None:
    # the notes are signed with a role, not with the name of whoever ran this script
    _tracker_runtime._try_getuser = lambda: "instructor"

    work = Path(tempfile.mkdtemp(prefix="bpm-solution-"))
    # pmprov stores where each value file was written. Recording from inside the folder, with relative paths, keeps the folder of
    # whoever runs this script out of the history; the notebook points the names at its own folder when it loads the zip.
    os.chdir(work)
    storage = DuckDBSQLiteBackend(db_path=Path("provenance.db"), artifact_dir=Path("artifacts"))
    rt = RuntimeTracker(storage=storage, session_id="model-solution", history_name=kit.SOLUTION_HISTORY_NAME, agent_id=AUTHOR)
    adapter = PmprovAdapter(rt)
    record, state_of = kit.analyst_recorder(rt, adapter)

    # --- the first look at the log -------------------------------------------------------------------------------------------
    event_log = record(["event_log"], kit.load_event_log, "data/bpi2017.parquet")
    log_summary = record(["log_summary"], kit.summarise_log, event_log)
    activities = record(["activities"], kit.activity_overview, event_log)
    attributes = record(["attributes"], kit.attribute_overview, event_log)
    record(["log_sample"], kit.log_sample, event_log, 100)

    # --- the maps of the two lifecycles -----------------------------------------------------------------------------------------
    activity_log = record(["activity_log"], kit.case_activity_timestamp, event_log)
    application_activities = record(["application_activities"], kit.activities_starting_with, event_log, "A_")
    application_figure, application_meta = record(
        ["application_figure", "application_meta"], kit.draw_map,
        activity_log, application_activities, "set_based", True, True, 650, name="draw_application_map",
    )
    start_share = record(["start_share"], kit.share_of_cases_starting_with, event_log, "A_Create Application")
    case_count = record(["case_count"], kit.count_cases, event_log)
    offer_activities = record(["offer_activities"], kit.activities_starting_with, event_log, "O_")
    offer_figure, offer_meta = record(
        ["offer_figure", "offer_meta"], kit.draw_map,
        activity_log, offer_activities, "set_based", True, True, 650, name="draw_offer_map",
    )

    # --- 1a: the schema of A_Create Application ----------------------------------------------------------------------------------
    create_coverage = record(["create_coverage"], kit.attribute_coverage, event_log, "A_Create Application")
    create_schema = record(["create_schema"], kit.attributes_with_a_value, create_coverage)

    # --- 1b: missing values in that schema ---------------------------------------------------------------------------------------
    missing_values, outside_schema = record(["missing_values", "outside_schema"], kit.missing_values_of, create_coverage, create_schema)

    # --- 1c: attributes used by more than one activity ---------------------------------------------------------------------------
    attribute_reuse = record(["attribute_reuse"], kit.attribute_reuse_of, event_log)
    offer_id_log = record(["offer_id_log"], kit.events_carrying, event_log, "OfferID")
    offer_id_activities = record(["offer_id_activities"], kit.distinct_activities, offer_id_log)
    offer_id_figure, offer_id_meta = record(
        ["offer_id_figure", "offer_id_meta"], kit.draw_map,
        offer_id_log, offer_id_activities, "set_based", True, False, 650, name="draw_offer_id_map",
    )
    credit_score_log = record(["credit_score_log"], kit.events_carrying, event_log, "CreditScore")
    credit_score_activities = record(["credit_score_activities"], kit.distinct_activities, credit_score_log)
    credit_score_figure, credit_score_meta = record(
        ["credit_score_figure", "credit_score_meta"], kit.draw_map,
        credit_score_log, credit_score_activities, "set_based", True, False, 400, name="draw_credit_score_map",
    )

    # --- the facts the notes quote, read from the results above ---------------------------------------------------------------------
    by_family = activities.groupby("family")["activity"].count()
    schema_names = ", ".join(create_schema["attribute"])
    missing_total = int(missing_values["missing"].sum())
    reused = attribute_reuse[attribute_reuse["activities"] > 1]
    only_one = attribute_reuse[attribute_reuse["activities"] == 1]
    everywhere = attribute_reuse[attribute_reuse["activities"] == int(log_summary["activities"])]
    filled_rarely = attributes[attributes["% of events"] < 50]["attribute"].tolist()
    rarest_ceiling = attributes[attributes["% of events"] < 50]["% of events"].max()
    only_one_where = sorted(set(only_one["carried by"]))  # the activity (or activities) that those attributes live on
    assert only_one_where == ["O_Create Offer"], only_one_where  # the notes below say so
    print(f"log: {log_summary}")
    print(f"families: {by_family.to_dict()}  start share: {start_share:.1f}%")
    print(f"schema ({len(create_schema)}): {schema_names}")
    print(f"missing values: {missing_total}; outside the schema ({len(outside_schema)}): {outside_schema}")
    print(f"attributes: {len(attribute_reuse)}; on more than one activity: {len(reused)}; on every activity: {len(everywhere)}; on one: {only_one['attribute'].tolist()}")
    print(f"OfferID: {offer_id_activities}; CreditScore: {credit_score_activities}; filled rarely: {filled_rarely}")

    # --- the notes ----------------------------------------------------------------------------------------------------------------------
    # (target, name of the artifact in the notebook, granularity, title, text, tags)
    notes = [
        ("activities", "activity_overview", "dataset",
         "Three families of activities: A_, O_ and W_",
         f"The log has {log_summary['activities']} activities in three families: {by_family['Application']} application states (A_), "
         f"{by_family['Offer']} offer states (O_) and {by_family['Workflow']} workflow activities (W_). Only A_Create Application, "
         "A_Concept, A_Accepted, O_Create Offer, O_Created and W_Complete application occur in every case. I will work with the "
         "application states for the schema question and with the offer states where an attribute turns out to belong to offers.",
         ("first look",)),
        ("attributes", "attribute_overview", "dataset",
         "Most columns are filled on every event; the offer columns are not",
         f"{log_summary['columns']} columns. {len(attributes[attributes['% of events'] == 100])} of them have a value on every one of the "
         f"{log_summary['events']:,} events. The others ({', '.join(filled_rarely)}) are filled on at most {rarest_ceiling:.0f}% of the "
         "events, so they belong to something that happens on few events: offers. This already suggests that the schema of an activity is "
         "smaller than the list of columns.",
         ("first look", "finding")),
        ("create_schema", "create_schema", "dataset",
         f"(a) A_Create Application carries {len(create_schema)} attributes",
         f"Its schema is the set of attributes that take a value on its events: {schema_names}. These are the attributes of every event of the "
         "log (who did it, when, which event it is) and the three attributes of the loan application itself (LoanGoal, ApplicationType, "
         "RequestedAmount). It carries none of the offer attributes.",
         ("1a", "finding")),
        ("application_figure", "map_application_states", "chart_selection",
         "(a) Every application starts with A_Create Application",
         f"The map of the application states over all {case_count:,} cases starts with A_Create Application in {start_share:.1f}% of the cases. "
         "So the schema above is the data every application enters the process with, and the only activity that has it first.",
         ("1a",)),
        ("missing_values", "missing_values", "dataset",
         "(b) No attribute of the schema has missing values",
         f"Of the {len(missing_values)} attributes of the schema, {missing_total} events lack a value: every attribute is filled on every "
         f"A_Create Application event. The {len(outside_schema)} attributes that are empty on this activity are all offer attributes "
         f"({', '.join(outside_schema)}). They are not part of its schema, so an empty value there is not a missing value.",
         ("1b", "finding")),
        ("attribute_reuse", "attribute_reuse", "dataset",
         f"(c) {len(reused)} of {len(attribute_reuse)} attributes are used by more than one activity",
         f"{len(everywhere)} attributes have a value on all {log_summary['activities']} activities; they describe the event or the application "
         f"and are re-used everywhere. Beyond those, OfferID is shared by some activities. The remaining {len(only_one)} take a value on a "
         f"single activity, {only_one_where[0]} ({', '.join(only_one['attribute'])}). To see where an attribute lives I draw the map of the "
         "events that carry it: its activities are the nodes.",
         ("1c", "finding")),
        ("offer_id_figure", "map_offer_id_carriers", "chart_selection",
         "(c) OfferID is re-used",
         f"The map of the events that carry OfferID has {len(offer_id_activities)} activities: {', '.join(offer_id_activities)}. "
         "They are the offer states from O_Created onwards: the same offer identifier is repeated on each of them. It is not on "
         "O_Create Offer, the activity where the offer is made.",
         ("1c", "finding")),
        ("credit_score_figure", "map_credit_score_carriers", "chart_selection",
         "(c) CreditScore is not re-used",
         f"The map of the events that carry CreditScore has {len(credit_score_activities)} activity: {', '.join(credit_score_activities)}. "
         "It is recorded once, when the offer is made, and not repeated on the later offer states.",
         ("1c", "finding")),
    ]
    for target, artifact, granularity, title, text, tag_names in notes:
        state = state_of(target)
        adapter.persist_annotation(
            state,
            {
                "title": title,
                "note": f"{title}. {text}",  # pmprov keeps a note as one text, and the side panel lists its first words
                "tags": tags(*tag_names),
                "artifacts": [{"artifactId": state, "artifactName": artifact, "granularity": granularity, "detail": None}],
            },
        )
    adapter.settle()

    # pmprov pins the newest DuckDB, whose files an older DuckDB refuses to open ("version number 999"), and a hosted notebook may
    # run an older one. The shipped history is therefore copied into a database of the oldest format: every DuckDB can read it.
    with _connect_lock:
        _convert = duckdb.connect()
        _convert.execute("ATTACH 'provenance.db' AS source (READ_ONLY)")
        _convert.execute(f"ATTACH 'portable.db' AS target (STORAGE_VERSION '{PORTABLE_STORAGE_VERSION}')")
        _convert.execute("COPY FROM DATABASE source TO target")
        _convert.close()
    for _name in ("provenance.db", "provenance.db.wal", "portable.db.wal"):
        (work / _name).unlink(missing_ok=True)
    (work / "portable.db").rename(work / "provenance.db")

    data, left_out = zip_provenance(work)
    os.chdir(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    print(f"{len(notes)} notes written; {output} is {len(data) / 1024:.0f} kB (left out as too big: {[name for name, _ in left_out]})")
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
