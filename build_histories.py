"""Record the two analyses that the reviewer notebooks replay: the LC maps tutorial and the model solution of Tasks 8 to 10.

Each analysis is made with the same steps as the student notebook (`bpm_kit.draw_map` and friends, through `record`), and its
notes are written with the same panel adapter, so it replays exactly like a student's work. The numbers in the notes are computed
from the logs here, so they always match the maps.

    python build_histories.py                    # writes histories/tutorial.zip and histories/model-solution.zip
    python build_histories.py --push             # also stores them on the course server (keys from the environment)

`--push` reads TUTORIAL_KEY and SOLUTION_KEY (and PMPROV_SYNC_URL, default https://provenance.alvispace.com). The course of each
key must be open when you push; close it afterwards so that the stored analysis cannot be overwritten.

Notes follow one convention, which the tutorial teaches: a note tagged `intent` says what a map is for and is written right after
it appears; a note tagged `finding` says what a table or map shows. Every note carries one of these two tags, and then the tags
that group it: the technique in the tutorial (`rework`, `leakage`, ...), the task in the solution (`task8`, `task9`, `task10`).
A note's tags belong to that note alone.
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
    """One recorded analysis: steps through `record`, notes through the panel adapter."""

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


def build_tutorial(work: Path) -> Path:
    s = Session(work / "tutorial", kit.TUTORIAL_HISTORY_NAME)
    log = s.record(["event_log"], kit.load_event_log, kit.DECLARATIONS)
    s.record(["log_summary"], kit.summarise_log, log)
    overview = s.record(["activities"], kit.activity_overview, log)

    SUB, APP_ADM, FIN, REQ, PAY = (
        "Declaration SUBMITTED by EMPLOYEE", "Declaration APPROVED by ADMINISTRATION", "Declaration FINAL_APPROVED by SUPERVISOR",
        "Request Payment", "Payment Handled",
    )
    APP_BUD, REJ_EMP, SAVED = "Declaration APPROVED by BUDGET OWNER", "Declaration REJECTED by EMPLOYEE", "Declaration SAVED by EMPLOYEE"
    REJ_APPROVERS = ["Declaration REJECTED by ADMINISTRATION", "Declaration REJECTED by BUDGET OWNER", "Declaration REJECTED by SUPERVISOR"]
    FOLD = {"Rejected by an approver": REJ_APPROVERS}

    t = traces(log)
    n = len(t)
    variants = t.apply(tuple).value_counts()
    main = variants.get((SUB, APP_ADM, FIN, REQ, PAY), 0)
    main_budget = variants.get((SUB, APP_ADM, APP_BUD, FIN, REQ, PAY), 0)
    last = t.str[-1].value_counts()
    submissions = t.apply(lambda tr: tr.count(SUB))
    both = t.apply(lambda tr: PAY in tr and REJ_EMP in tr).sum()
    neither = t.apply(lambda tr: PAY not in tr and REJ_EMP not in tr).sum()
    case_share = overview.set_index("activity")["% of cases"]
    rejected_by_approver = t.apply(lambda tr: any(a in REJ_APPROVERS for a in tr)).sum()

    # 1. the table of activities
    s.intent(
        "activities", "activity_overview", granularity="dataset",
        text="See which activities the log records and how common each one is, before drawing any map.",
    )
    s.finding(
        "activities", "activity_overview", granularity="dataset", tags=["first look"],
        text=(
            f"The log has {n:,} declarations and {len(overview)} activities. Five activities occur in more than 95% of the "
            f"declarations (submission, approval by administration, final approval by the supervisor, payment request and payment). "
            f"Rejections are much rarer: a rejection by administration occurs in {case_share[REJ_APPROVERS[0]]}% of the declarations."
        ),
    )

    # 2. all activities, set-based: mainstream and exceptional behavior, leakage
    meta = s.map(log, None, "set_based")
    s.intent(
        "map_figure", "process_map",
        "Draw every activity with the set-based abstraction to separate the mainstream behavior from the exceptions.",
    )
    s.finding(
        "map_figure", "process_map", tags=["mainstream vs exceptional"],
        text=(
            f"Two thick bands carry most declarations: submission, approval by administration, final approval, payment request "
            f"and payment ({main:,} declarations, {pct(main, n)}), and the same path with an approval by the budget owner "
            f"({main_budget:,}, {pct(main_budget, n)}). Every other path is a thin band, so the exceptional behavior is clearly "
            f"separated from the mainstream."
        ),
    )
    s.finding(
        "map_figure", "process_map", tags=["leakage"],
        text=(
            f"Dark nodes mark where paths end ({meta['nodes_leakage_gt_0']} nodes). Apart from the payment, {last.get(REJ_EMP, 0):,} "
            f"declarations end right after REJECTED by EMPLOYEE, and {last.get(SAVED, 0):,} consist of SAVED by EMPLOYEE only: "
            f"they were saved but never submitted."
        ),
    )

    # 3. the same, last-activity-based: knockout stages, and why a back edge is ambiguous
    s.map(log, None, "last_activity_based")
    s.intent("map_figure", "process_map", 
        "Switch to the last-activity abstraction (the directly-follows graph) to see at which stages a declaration is stopped."
    )
    s.finding(
        "map_figure", "process_map", tags=["knockout structure"],
        text=(
            "The map has one node per activity. A rejection can happen at each approval stage (administration, budget owner, "
            "supervisor), and a rejection is normally followed by REJECTED by EMPLOYEE. Here a rejection does not end the case: the back edge "
            "to SUBMITTED by EMPLOYEE shows that most rejected declarations are submitted again."
        ),
    )
    s.finding(
        "map_figure", "process_map", tags=["abstractions"],
        text=(
            "In this abstraction the back edge forms a cycle, and a cycle alone does not tell whether an activity is repeated "
            "(rework) or only ordered differently. The set-based map shows repetition as a self-loop, which is unambiguous."
        ),
    )

    # 4. fold the rejections by approvers, set-based: rework as a self-loop
    s.map(log, None, "set_based", folds=FOLD)
    s.intent("map_figure", "process_map", 
        "Fold the rejections by administration, budget owner and supervisor into one activity, because the question is whether "
        "a declaration was rejected, not by whom. Then look at repetition in the set-based map."
    )
    resubmitted = int((submissions >= 2).sum())
    s.finding(
        "map_figure", "process_map", tags=["folding", "rework"],
        text=(
            f"With the fold, the map has fewer and wider bands. {rejected_by_approver:,} declarations ({pct(rejected_by_approver, n)}) "
            f"are rejected by an approver at least once. The self-loops show rework: {resubmitted:,} declarations are submitted "
            f"more than once."
        ),
    )

    # 5. sequence-based on two activities: how often the loop is repeated
    s.map(log, [SUB] + REJ_APPROVERS, "sequence_based", folds=FOLD)
    s.intent("map_figure", "process_map", "Count how many times a declaration goes through the rejection loop, with only the submission and the fold selected.")
    counts = submissions.value_counts().sort_index()
    s.finding(
        "map_figure", "process_map", tags=["rework", "variants"],
        text=(
            f"The sequence-based map is the prefix tree: every node is a distinct beginning of a path. {counts.get(1, 0):,} "
            f"declarations are submitted once, {counts.get(2, 0):,} twice, {counts.get(3, 0):,} three times and "
            f"{int(counts[counts.index >= 4].sum()):,} four times or more. The empty trace node holds the {counts.get(0, 0):,} "
            f"declarations that were never submitted."
        ),
    )

    # 6. outcome candidates
    s.map(log, [PAY, REJ_EMP], "set_based")
    s.intent("map_figure", "process_map", 
        "Check whether payment and REJECTED by EMPLOYEE can serve as the outcomes of a declaration: every declaration should "
        "have exactly one of them."
    )
    s.finding(
        "map_figure", "process_map", tags=["outcome distribution"],
        text=(
            f"They are not mutually exclusive: {both:,} declarations reach both, because a rejection is usually followed by a new "
            f"submission and a payment. The empty trace node holds {neither:,} declarations with neither. REJECTED by EMPLOYEE is "
            f"therefore an intermediate state, not an outcome."
        ),
    )

    # 7. outcomes as where a path ends
    s.map(log, None, "last_activity_based", folds=FOLD)
    s.intent("map_figure", "process_map", "Use where a declaration ends as its outcome: draw all activities, with the fold, in the last-activity abstraction.")
    ended_after_approver = int(sum(last.get(a, 0) for a in REJ_APPROVERS))
    s.finding(
        "map_figure", "process_map", tags=["outcome distribution"],
        text=(
            f"The number of paths that end in a node (shown on hover) is a mutually exclusive and complete outcome distribution: "
            f"{last.get(PAY, 0):,} declarations end with the payment ({pct(last.get(PAY, 0), n)}), {last.get(REJ_EMP, 0):,} with "
            f"a rejection that was not followed by a new submission, {last.get(SAVED, 0):,} as saved only, and "
            f"{ended_after_approver} right after a rejection by an approver (still open when the log was extracted)."
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

    # facts for the notes
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
