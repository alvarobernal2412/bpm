"""Record the two analyses that the reviewer notebooks replay: the LC maps tutorial and the model solution of Tasks 8 to 10.

Each analysis is made with the same steps as the student notebook (`bpm_kit.draw_map` and friends, through `record`), and its
annotations are written with the same panel adapter, so it replays exactly like a student's work. The numbers in the annotations are computed
from the logs here, so they always match the maps.

    python build_histories.py                    # writes histories/tutorial.zip and histories/model-solution.zip
    python build_histories.py --push             # also stores them on the course server (keys from the environment)

`--push` reads TUTORIAL_KEY and SOLUTION_KEY (and PMPROV_SYNC_URL, default https://provenance.alvispace.com). The course of each
key must be open when you push; close it afterwards so that the stored analysis cannot be overwritten.

Annotations follow one convention, which the tutorial teaches: an annotation tagged `intent` says what a map is for and is written right after
it appears; an annotation tagged `finding` says what a table or map shows. Every annotation carries one of these two tags, and then the tags
that group it: the technique in the tutorial (`rework`, `leakage`, ...), the task in the solution (`task8`, `task9`, `task10`).
An annotation's tags belong to that annotation alone.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bpm_kit as kit  # noqa: E402

warnings.filterwarnings("ignore", message=r"init_marimo\(\) was called but patch_marimo_ast_compile")


class Session:
    """One recorded analysis: steps through `record`, annotations through the panel adapter."""

    def __init__(self, folder: Path, history_name: str):
        from provenance_widget.pmprov_adapter import PmprovAdapter
        from tracker import init_marimo

        if folder.exists():
            shutil.rmtree(folder)
        (folder / "artifacts").mkdir(parents=True)
        self.folder = folder
        self.rt = init_marimo(
            history_name=history_name,
            branch_name="main",
            db_path=str(folder / "provenance.db"),
            artifact_dir=str(folder / "artifacts"),
            fresh=True,
        )
        self.adapter = PmprovAdapter(self.rt)
        self.record, self.state_of = kit.analyst_recorder(self.rt, self.adapter)

    def map(self, log, activities, map_type="set_based", folds=None, case_notion="application", allow_loops=True, show_empty=True):
        figure, meta = self.record(
            ["map_figure", "map_meta"],
            kit.draw_map, log, activities, map_type, allow_loops, show_empty, folds or {}, case_notion, 620,
            name="draw_map", replay_stored=False,
        )
        return meta

    def intent(self, target: str, artifact_name: str, text: str, tags=(), granularity="chart_selection"):
        """Why a table or map was made. Written right after it appears, before the findings, and picked on it."""
        self._note(target, artifact_name, text, ("intent", *tags), granularity)

    def finding(self, target: str, artifact_name: str, text: str, tags=(), granularity="chart_selection"):
        """What a table or map shows, picked on it."""
        self._note(target, artifact_name, text, ("finding", *tags), granularity)

    def _note(self, target, artifact_name, text, tags, granularity):
        state = self.state_of(target)
        picked = [{"artifactId": state, "artifactName": artifact_name, "granularity": granularity}]
        self.adapter.persist_annotation(state, {"note": text, "tags": [{"name": t} for t in tags], "artifacts": picked})

    def finish(self, zip_path: Path) -> Path:
        from provenance_widget.portable import zip_provenance

        self.rt.storage._executor.submit(lambda: None).result()  # let queued writes land
        old_storage_format(self.folder / "provenance.db")
        data, left_out = zip_provenance(self.folder)
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(data)
        print(f"{zip_path}: {len(data) / 1e6:.1f} MB; left out: {[name for name, _ in left_out]}")
        return self.folder


def old_storage_format(db: Path) -> None:
    """Rewrite the provenance database in DuckDB's oldest storage format. A recent DuckDB writes a format that older versions
    refuse to open ("version 999"), and molab runs an older DuckDB than a recent pmprov installs; the old format opens everywhere."""
    import duckdb
    from tracker.storage import _connect_lock

    target = db.with_name("portable.db")
    target.unlink(missing_ok=True)
    with _connect_lock:
        con = duckdb.connect()
        con.execute(f"ATTACH '{db.as_posix()}' AS source (READ_ONLY)")
        con.execute(f"ATTACH '{target.as_posix()}' AS target (STORAGE_VERSION 'v1.0.0')")
        con.execute("COPY FROM DATABASE source TO target")
        con.close()
    for leftover in (db, db.with_name(db.name + ".wal"), target.with_name(target.name + ".wal")):
        leftover.unlink(missing_ok=True)
    target.rename(db)


def traces(log, prefix_filter=None, case_column=kit.CASE_ID):
    events = log if prefix_filter is None else log[prefix_filter(log)]
    events = events[events[case_column].notna()]
    events = events.sort_values([case_column, kit.TIMESTAMP], kind="stable")
    return events.groupby(case_column)[kit.ACTIVITY].apply(list)


def pct(part, whole):
    return f"{part / whole * 100:.1f}%"


# --- the tutorial --------------------------------------------------------------------------------------------------------------
# It teaches how to read the maps on the BPI 2017 log, on its workflow activities (W_) only. The tasks ask for the application (A_)
# and offer (O_) lifecycles and for the outcomes, so nothing here shows what they should find.


def build_tutorial(work: Path) -> Path:
    s = Session(work / "tutorial", kit.TUTORIAL_HISTORY_NAME)
    log = s.record(["event_log"], kit.load_event_log, kit.BPI2017)
    summary = s.record(["log_summary"], kit.summarise_log, log)
    overview = s.record(["activities"], kit.activity_overview, log)
    names = kit.distinct_activities(log)
    W = [a for a in names if a.startswith("W_")]
    COMPLETE, CALL, VALIDATE, INCOMPLETE, LEADS = (
        "W_Complete application", "W_Call after offers", "W_Validate application", "W_Call incomplete files", "W_Handle leads",
    )
    # the names are taken from the log: one of them ends with a space ("W_Shortened completion ")
    RARE = [a for a in W if a.strip() in ("W_Assess potential fraud", "W_Shortened completion", "W_Personal Loan collection")]
    assert len(RARE) == 3, RARE
    FOLD = {"Rare workflow activities": RARE}

    t = traces(log, lambda l: l[kit.ACTIVITY].str.startswith("W_"))
    n = summary["cases"]
    in_cases = overview.set_index("activity")["cases"]
    last = t.str[-1].value_counts()
    order = t.apply(lambda tr: tuple(dict.fromkeys(tr))).value_counts()
    main = order.index[0]
    rare_cases = int(t.apply(lambda tr: any(a in RARE for a in tr)).sum())
    events_per_case = t.apply(lambda tr: tr.count(INCOMPLETE))
    never = int((events_per_case == 0).sum())
    most_common = events_per_case[events_per_case > 0].value_counts().idxmax()
    sequences = int(t.apply(tuple).nunique())

    # 1. the table of activities
    s.intent(
        "activities", "activity_overview", granularity="dataset",
        text="See which activities the log records, in which families, and how common each one is, before drawing any map.",
    )
    s.finding(
        "activities", "activity_overview", granularity="dataset", tags=["first look"],
        text=(
            f"The log has {n:,} loan applications and {summary['activities']} activities in three families: A_ (the state of the "
            f"application), O_ (the state of an offer) and W_ (work done by an employee). This tutorial maps only the {len(W)} W_ "
            f"activities. One thing to keep in mind: a W_ activity is a piece of work, and every piece of work leaves several events "
            f"(scheduled, started, suspended, resumed, completed), all under the same name. The event counts are therefore much larger "
            f"than the case counts."
        ),
    )

    # 2. the W_ activities, set-based: mainstream and exceptional behavior, leakage, self-loops
    meta = s.map(log, W, "set_based")
    nodes_all = meta["total_nodes"]
    s.intent(
        "map_figure", "process_map",
        "Draw the workflow activities with the set-based abstraction to separate the mainstream behavior from the exceptions.",
    )
    s.finding(
        "map_figure", "process_map", tags=["mainstream vs exceptional"],
        text=(
            f"Every application performs {COMPLETE[2:]}, and {in_cases[CALL] / n * 100:.1f}% perform {CALL[2:]}; the thick bands of "
            f"the map are these two activities. The most common path is {' → '.join(a[2:] for a in main)} ({order.iloc[0]:,} "
            f"applications, {pct(order.iloc[0], n)}); {pct(int(in_cases[LEADS]), n)} of the applications start with {LEADS[2:]}. The "
            f"rare activities are thin bands: {RARE[0][2:].strip()} occurs in {in_cases[RARE[0]]:,} applications, {RARE[1][2:].strip()} in "
            f"{in_cases[RARE[1]]:,} and {RARE[2][2:].strip()} in {in_cases[RARE[2]]:,}."
        ),
    )
    s.finding(
        "map_figure", "process_map", tags=["leakage"],
        text=(
            f"Dark nodes mark where paths end ({meta['nodes_leakage_gt_0']} nodes; the tooltip gives the number). Most workflows end "
            f"after {VALIDATE[2:]} ({last[VALIDATE]:,}, {pct(last[VALIDATE], n)}), after {CALL[2:]} ({last[CALL]:,}, "
            f"{pct(last[CALL], n)}) or after {INCOMPLETE[2:]} ({last[INCOMPLETE]:,}, {pct(last[INCOMPLETE], n)}). A workflow that "
            f"ends is not an outcome by itself: it only says what the last piece of work was."
        ),
    )
    s.finding(
        "map_figure", "process_map", tags=["rework"],
        text=(
            f"Loops on a node mean that events of the same activity follow each other. Here they must be read with care: one piece "
            f"of work has several events, so a self-loop on {INCOMPLETE[2:]} or {VALIDATE[2:]} does not by itself say that the work "
            f"was repeated."
        ),
    )

    # 3. the same, last-activity-based
    meta_last = s.map(log, W, "last_activity_based")
    s.intent(
        "map_figure", "process_map",
        "Switch to the last-activity abstraction (the directly-follows graph) and compare it with the set-based map.",
    )
    s.finding(
        "map_figure", "process_map", tags=["abstractions"],
        text=(
            f"The map has {meta_last['total_nodes']} nodes, against {nodes_all} in the set-based map: one node per activity, with "
            f"arrows for the activities that directly follow each other. It is the smallest map, but a cycle between two activities "
            f"can mean a repetition or only a different order, and the map cannot tell which. The set-based map separates them: a "
            f"repetition is a self-loop."
        ),
    )

    # 4. fold the rare activities
    meta_fold = s.map(log, W, "set_based", folds=FOLD)
    s.intent(
        "map_figure", "process_map",
        "Fold the three rare activities into one, because the question is whether a rare activity occurred, not which one. Then "
        "look at the set-based map again.",
    )
    s.finding(
        "map_figure", "process_map", tags=["folding"],
        text=(
            f"The map shrinks from {nodes_all} to {meta_fold['total_nodes']} nodes. The fold is one band of {rare_cases:,} "
            f"applications ({pct(rare_cases, n)}) that perform at least one rare activity, which is easier to follow than three "
            f"separate bands. What is lost is the difference between the three."
        ),
    )

    # 5. sequence-based on one activity
    meta_seq = s.map(log, [INCOMPLETE], "sequence_based")
    s.intent(
        "map_figure", "process_map",
        f"Count how many events of {INCOMPLETE[2:]} an application has, selecting only that activity in the sequence-based "
        "abstraction.",
    )
    s.finding(
        "map_figure", "process_map", tags=["variants", "rework"],
        text=(
            f"The sequence-based map is the prefix tree: every node is a distinct beginning of a path, so with one activity each step "
            f"to the right is one more event of it. {never:,} applications have none (the empty trace node). Among the others, the "
            f"most common number of events is {most_common}, because a piece of work leaves several events: this counts events, not "
            f"pieces of work. With all eight activities the same abstraction would split the applications into {sequences:,} distinct "
            f"sequences, far too many to read: use it on few activities."
        ),
    )
    return s.finish(HERE / kit.TUTORIAL_ZIP)


# --- the model solution of Tasks 8 to 10 --------------------------------------------------------------------------------------


def build_solution(work: Path) -> Path:
    s = Session(work / "model-solution", kit.HISTORY_NAME)
    log = s.record(["event_log"], kit.load_event_log, kit.BPI2017)
    summary = s.record(["log_summary"], kit.summarise_log, log)
    overview = s.record(["activities"], kit.activity_overview, log)
    names = kit.distinct_activities(log)
    A = [a for a in names if a.startswith("A_")]
    O = [a for a in names if a.startswith("O_") and a != "O_Create Offer"]
    n = summary["cases"]

    # facts for the annotations
    ta = traces(log, lambda l: l[kit.ACTIVITY].str.startswith("A_"))
    short = ta.apply(lambda tr: [a[2:] for a in tr])
    no_submitted = int(short.apply(lambda tr: "Submitted" not in tr).sum())
    validating_twice = int(short.apply(lambda tr: tr.count("Validating") >= 2).sum())
    incomplete = int(short.apply(lambda tr: "Incomplete" in tr).sum())
    completed = int(short.apply(lambda tr: "Complete" in tr).sum())

    def follows(tr, a, b):
        return any(x == a and y == b for x, y in zip(tr, tr[1:]))

    incomplete_pending = int(short.apply(lambda tr: follows(tr, "Incomplete", "Pending")).sum())
    cancelled = int(short.apply(lambda tr: "Cancelled" in tr).sum())
    cancelled_after_complete = int(short.apply(lambda tr: follows(tr, "Complete", "Cancelled")).sum())
    denied = int(short.apply(lambda tr: "Denied" in tr).sum())
    denied_after_validating = int(short.apply(lambda tr: follows(tr, "Validating", "Denied")).sum())
    pending = int(short.apply(lambda tr: "Pending" in tr).sum())
    no_outcome = int(short.apply(lambda tr: not ({"Pending", "Denied", "Cancelled"} & set(tr))).sum())
    two_outcomes = int(short.apply(lambda tr: len({"Pending", "Denied", "Cancelled"} & set(tr)) > 1).sum())

    to = traces(log[log["OfferID"].notna()], case_column="OfferID")
    offers = len(to)
    offer_variants = to.apply(tuple).nunique()
    so = to.apply(lambda tr: [a[2:] for a in tr])
    o_returned = int(so.apply(lambda tr: "Returned" in tr).sum())
    o_accepted = int(so.apply(lambda tr: "Accepted" in tr).sum())
    o_cancelled = int(so.apply(lambda tr: "Cancelled" in tr).sum())
    o_refused = int(so.apply(lambda tr: "Refused" in tr).sum())
    o_cancel_unreturned = int(so.apply(lambda tr: "Cancelled" in tr and "Returned" not in tr).sum())
    o_refused_unreturned = int(so.apply(lambda tr: "Refused" in tr and "Returned" not in tr).sum())
    o_online_only = int(so.apply(lambda tr: "Sent (online only)" in tr).sum())
    o_open = int(so.apply(lambda tr: not ({"Accepted", "Cancelled", "Refused"} & set(tr))).sum())
    o_repeat = int(so.apply(lambda tr: len(tr) != len(set(tr))).sum())
    per_app = log[log["OfferID"].notna()].groupby(kit.CASE_ID)["OfferID"].nunique()
    app_variants = traces(log, lambda l: l[kit.ACTIVITY].isin(O)).apply(tuple).nunique()

    # first look
    s.intent(
        "activities", "activity_overview", granularity="dataset",
        text="Get an overview of the activities of the log and of the three families before drawing a map.",
    )
    s.finding(
        "activities", "activity_overview", granularity="dataset", tags=["first look"],
        text=(
            f"The log has {n:,} applications and {summary['activities']} activities: {len(A)} application states (A_), "
            f"{len(O) + 1} offer states (O_) and {len(names) - len(A) - len(O) - 1} workflow activities (W_). "
            f"The application states describe one lifecycle per case, which makes them the primary subprocess to map first."
        ),
    )

    # Task 8: the application lifecycle
    s.map(log, A, "set_based")
    s.intent("map_figure", "process_map", tags=["task8"], text="Task 8: map only the application states (A_) with all of them selected, using the set-based abstraction.")
    s.finding(
        "map_figure", "process_map", tags=["task8"],
        text=(
            f"Mainstream behavior: every application goes through Create Application, Concept and Accepted, and "
            f"{completed:,} ({pct(completed, n)}) also reach Complete, which forms the thick main band of the map. "
            f"A_Submitted is skipped in {no_submitted:,} applications ({pct(no_submitted, n)}): these were created by the bank, "
            f"not by the customer on the website."
        ),
    )
    s.finding(
        "map_figure", "process_map", tags=["task8"],
        text=(
            f"Knockout structure: {cancelled:,} applications are cancelled, {cancelled_after_complete:,} of them directly after "
            f"A_Complete, that is, while the bank waits for the customer to return the offer. {denied:,} applications are denied, "
            f"{denied_after_validating:,} of them directly after A_Validating, so most denials come late, after the documents were "
            f"checked. Earlier identification of these cases could save processing effort."
        ),
    )
    s.finding(
        "map_figure", "process_map", tags=["task8"],
        text=(
            f"Rework: {incomplete:,} applications ({pct(incomplete, n)}) reach A_Incomplete at least once, and "
            f"{validating_twice:,} are validated two or more times; the set-based map shows this repetition as self-loops."
        ),
    )
    s.map(log, A, "last_activity_based")
    s.intent("map_figure", "process_map", tags=["task8"], text="Task 8: check the transitions out of A_Incomplete in the last-activity abstraction.")
    s.finding(
        "map_figure", "process_map", tags=["task8"],
        text=(
            f"Unexpected ordering: in {incomplete_pending:,} applications A_Incomplete is followed directly by A_Pending, without a "
            f"new A_Validating. According to the process description, missing documents should be checked again before the loan "
            f"becomes final."
        ),
    )

    # Task 9: the offer lifecycle
    s.map(log, O, "set_based")
    s.intent("map_figure", "process_map", tags=["task9"], text=
        "Task 9: map the offer states without O_Create Offer, first with one path per loan application as the task describes."
    )
    s.finding(
        "map_figure", "process_map", tags=["task9"],
        text=(
            f"With one path per application, the offers of an application are mixed in one path: there are {app_variants:,} "
            f"sequential variants, and a state such as O_Created can appear several times per path because an application can "
            f"have several offers ({int((per_app > 1).sum()):,} applications have more than one)."
        ),
    )
    s.map(log, O, "set_based", case_notion="offer")
    s.intent("map_figure", "process_map", tags=["task9"], text="Task 9: draw one path per offer instead (each path is an offer, grouped by OfferID) to see the lifecycle of a single offer.")
    s.finding(
        "map_figure", "process_map", tags=["task9"],
        text=(
            f"Per offer, the map shows {offers:,} offers and only {offer_variants} variants. Every offer starts with O_Created and "
            f"is then sent, almost always by mail and online ({o_online_only:,} offers are sent online only). No offer state is "
            f"repeated ({o_repeat} offers with a repetition)."
        ),
    )
    s.finding(
        "map_figure", "process_map", tags=["task9"],
        text=(
            f"An offer ends accepted ({o_accepted:,}), cancelled ({o_cancelled:,}) or refused ({o_refused:,}). Acceptance always "
            f"follows O_Returned, whereas {o_cancel_unreturned:,} cancellations and {o_refused_unreturned:,} refusals happen "
            f"without a returned offer. {o_open} offers have not ended yet."
        ),
    )

    # Task 10: the outcome distribution
    s.map(log, ["A_Pending", "A_Denied", "A_Cancelled"], "set_based")
    s.intent("map_figure", "process_map", tags=["task10"], text=
        "Task 10: take the final application states (A_Pending, A_Denied, A_Cancelled) as candidate outcomes, keep empty traces "
        "visible, and check that every case has exactly one."
    )
    s.finding(
        "map_figure", "process_map", tags=["task10"],
        text=(
            f"No path reaches two of these states ({two_outcomes} applications), so the outcomes are mutually exclusive. The "
            f"empty trace node holds {no_outcome} applications without any of them; adding them as a fourth outcome, still "
            f"running, makes the set complete."
        ),
    )
    s.finding(
        "map_figure", "process_map", tags=["task10"],
        text=(
            f"Outcome distribution: {pending:,} granted ({pct(pending, n)}), {cancelled:,} cancelled ({pct(cancelled, n)}), "
            f"{denied:,} denied ({pct(denied, n)}) and {no_outcome} still running ({pct(no_outcome, n)}). One application in three "
            f"is cancelled, mostly by the customer after the offers were sent, which is more than three times the number of denials."
        ),
    )
    return s.finish(HERE / kit.SOLUTION_ZIP)


def push(folder: Path, key: str, url: str) -> None:
    from provenance_widget.sync import Sync

    sync = Sync(url, key, folder)
    sync.push()
    print(f"{folder.name}: {sync.status.message}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--push", action="store_true", help="also store the analyses on the course server")
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix="bpm-build-"))
    tutorial = build_tutorial(work)
    solution = build_solution(work)
    if args.push:
        url = os.environ.get("PMPROV_SYNC_URL", "https://provenance.alvispace.com")
        for folder, variable in ((tutorial, "TUTORIAL_KEY"), (solution, "SOLUTION_KEY")):
            if os.environ.get(variable):
                push(folder, os.environ[variable], url)
            else:
                print(f"{variable} is not set; {folder.name} was not pushed.")
