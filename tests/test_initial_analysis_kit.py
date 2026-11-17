import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import initial_analysis_kit as kit  # noqa: E402

C, A, T = kit.CASE_ID, kit.ACTIVITY, kit.TIMESTAMP


def make_log(naive=False) -> pd.DataFrame:
    t0 = pd.Timestamp("2016-01-01 08:00:00", tz=None if naive else "UTC")
    rows = [
        # case, activity, minutes, lifecycle, OfferID (only O_ events), LoanGoal (case level)
        ("c1", "A_Create", 0, "complete", None, "Car"),
        ("c1", "A_Create", 0, "complete", None, "Car"),  # exact duplicate
        ("c1", "O_Create", 10, "complete", "o1", "Car"),
        ("c1", "A_Done", 20, "complete", None, "Car"),
        ("c2", "A_Create", 60, "complete", None, "House"),
        ("c2", "O_Create", 70, "complete", "o2", "House"),
        ("c3", "A_Create", 120, "schedule", None, "Car"),
    ]
    df = pd.DataFrame(rows, columns=[C, A, "minutes", "lifecycle_transition", "OfferID", "case_LoanGoal"])
    df[T] = [t0 + pd.Timedelta(minutes=m) for m in df.pop("minutes")]
    df["Constant"] = "x"
    df["Empty"] = np.nan
    return df[[C, A, T, "lifecycle_transition", "OfferID", "case_LoanGoal", "Constant", "Empty"]]


def init(log, timezone="UTC", granularity=None, enforce_order=False, window=(0, 10)):
    return kit.initialize_log(log, timezone, granularity, enforce_order, window, C, T)


def test_initialize_does_not_mutate_input():
    log = make_log()
    before = log.copy(deep=True)
    init(log, enforce_order=True)
    pd.testing.assert_frame_equal(log, before)


def test_initialize_drops_constant_empty_and_duplicates():
    out, messages, dupes = init(make_log())
    text = "\n".join(messages)
    assert "Dropped constant column 'Constant' with value: x" in text
    assert "Dropped empty column 'Empty'" in text
    assert "Removed 1 duplicate events in 1 groups of identical events" in text
    assert "Constant" not in out.columns and "Empty" not in out.columns
    assert len(out) == 6 and len(dupes) == 1


def test_initialize_converts_timezone():
    out, _, _ = init(make_log(), timezone="Europe/Zurich")
    assert str(out[T].dt.tz) == "Europe/Zurich"


def test_initialize_naive_timestamps_do_not_raise():
    out, _, _ = init(make_log(naive=True), timezone="Europe/Zurich")
    assert out[T].dt.tz is None


def test_initialize_window_with_no_cases_returns_empty_and_message():
    out, messages, _ = init(make_log(), window=(5000, 5001))  # days after the first event
    assert len(out) == 0
    assert any("kept 0 of 3 cases" in m for m in messages)


def test_initialize_single_case_log_keeps_mandatory_columns():
    log = make_log()
    one = log[log[C] == "c3"]
    frame = kit.time_frame(one, C, T)
    out, _, _ = init(one, window=(0, frame["stop"]))
    assert {C, A, T} <= set(out.columns)
    assert len(out) == 1


def test_granularity_rounds_timestamps():
    log = make_log()
    log.loc[log.index[3], T] += pd.Timedelta(seconds=40)
    out, messages, _ = init(log, granularity="minute")
    assert (out[T].dt.second == 0).all()
    assert any("Rounded" in m for m in messages)


def test_global_ordering_sorts_by_completion_time():
    log = make_log().iloc[::-1]
    out, messages, _ = init(log, enforce_order=True)
    assert out[T].is_monotonic_increasing
    assert any("globally ordered" in m for m in messages)


def test_time_frame_unit_hours_for_short_logs():
    frame = kit.time_frame(make_log(), C, T)
    assert frame["unit"] == "h"
    assert frame["start"] == pd.Timestamp("2016-01-01 08:00:00", tz="UTC")
    assert frame["stop"] >= frame["default"] >= 1


def test_time_frame_unit_days_for_long_logs():
    log = make_log()
    log.loc[log.index[-1], T] += pd.Timedelta(days=5)
    assert kit.time_frame(log, C, T)["unit"] == "D"


def test_ordering_summaries():
    case_summary, log_summary = kit.ordering_summaries(make_log(), C, T)
    assert case_summary["Cases"].iloc[0] == 3 and bool(case_summary["All ordered"].iloc[0])
    assert log_summary["Events"].iloc[0] == 7


def classified():
    log, _, _ = init(make_log())
    return log, kit.classify_attributes(log, C, A, T)


def test_classify_attributes_standard_case_and_schema():
    log, found = classified()
    assert found["mandatory"] == [C, A, T]
    assert "lifecycle_transition" in found["standard"]
    assert "case_LoanGoal" in found["case_features"]
    assert "OfferID" in found["case_features"]  # one offer per case in this log
    assert found["activity_schema"]["O_Create"] == ["OfferID"]
    assert found["activity_schema"]["A_Create"] == []
    assert found["activity_list"][0] == "A_Create"  # most frequent first
    assert found["activity_stats"]["A_Create"] == 3


def test_build_case_log_has_start_end_count_and_case_features():
    log, found = classified()
    cases = kit.build_case_log(log, C, A, T, found["case_features"])
    assert cases.loc["c1", "no_of_events"] == 3
    assert cases.loc["c1", "start_time"] < cases.loc["c1", "end_time"]
    assert cases.loc["c2", "case_LoanGoal"] == "House"


def test_build_case_log_runs_enrichment_code():
    log, found = classified()
    cases = kit.build_case_log(log, C, A, T, found["case_features"], "case_log['x'] = 1")
    assert (cases["x"] == 1).all()


def test_build_case_log_enrichment_error_propagates():
    log, found = classified()
    with pytest.raises(NameError):
        kit.build_case_log(log, C, A, T, found["case_features"], "case_log['x'] = not_defined")


def test_schema_views_incidence_and_local_attributes():
    log, found = classified()
    usages, partial = kit.schema_views(log, C, A, found["mandatory"], found["standard"], found["activity_stats"])
    assert usages.loc["A_Create", "incidence"] == 3
    assert usages.loc["O_Create", "local_attributes"] == ["OfferID"]
    assert usages.loc["A_Create", "local_attributes"] == []
    assert "OfferID" not in partial.columns  # used by one activity only: exclusive, not an overlap
    assert "Constant" not in usages.columns  # dropped at initialization


def test_timestamp_formats_lists_each_timestamp_column():
    table = kit.timestamp_formats(make_log())
    assert table["Timestamp column"].tolist() == [T]


def test_load_event_log_reads_parquet(tmp_path):
    path = tmp_path / "log.parquet"
    make_log().to_parquet(path)
    assert len(kit.load_event_log(path)) == 7


# --- views and the recorded widget values ---------------------------------------------------------------------------------------


def test_timestamp_components_and_selection():
    summary, prefixes = kit.timestamp_components(make_log())
    components, prefix = kit.select_timestamp_component(summary, prefixes, T)
    assert "Timestamp column" not in components.columns and len(components) > 0
    assert "Timestamp column" not in prefix.columns
    empty, _ = kit.select_timestamp_component(summary, prefixes, None)
    assert len(empty) == 0


def test_event_views_global_and_inspection_columns():
    log, found = classified()
    views = kit.event_views(log, found)
    assert list(views["global"].columns)[:3] == [C, A, T]
    assert "case_LoanGoal" not in views["global"].columns  # case-level attributes live in the case log
    assert views["inspection"].columns[-1] == "folded_data"


def test_local_attribute_view_common_attributes_of_selected_activities():
    log, found = classified()
    both = kit.local_attribute_view(log, ["O_Create"], found, hide_case_features=False)
    assert list(both.columns) == [C, A, T, "OfferID"]
    assert set(both[A]) == {"O_Create"}
    hidden = kit.local_attribute_view(log, ["O_Create"], found, hide_case_features=True)
    assert "OfferID" not in hidden.columns  # OfferID is also a case-level attribute here
    assert len(kit.local_attribute_view(log, [], found, hide_case_features=False)) == 0


class _Node:
    def __init__(self, name, params):
        self.operation = type("Op", (), {"name": name})()
        self.params = params


class _Adapter:
    def __init__(self, nodes):
        self._nodes = nodes

    def get_tree(self):
        return type("Tree", (), {"nodes": self._nodes})()


def test_params_at_returns_last_matching_step_up_to_the_cursor():
    adapter = _Adapter({
        "s1": _Node("initialize_log", {"timezone": "UTC"}),
        "s2": _Node("other", {}),
        "s3": _Node("initialize_log", {"timezone": "Europe/Zurich"}),
    })
    assert kit.params_at(adapter, None, "initialize_log") == {"timezone": "Europe/Zurich"}
    assert kit.params_at(adapter, "s2", "initialize_log") == {"timezone": "UTC"}
    assert kit.params_at(adapter, "s1", "other") is None


# --- the recorder: opening a stored analysis again must not repeat its steps ----------------------------------------------------


class _FakeStorage:
    def __init__(self, chain):
        self.children = {}
        parent = "root"
        for step in chain:
            self.children[parent] = [step]
            parent = step["output_state_id"]

    def load_child_steps(self, state_id):
        return self.children.get(state_id, [])


class _FakeRT:
    """What the recorder uses of pmprov's RuntimeTracker."""

    def __init__(self, chain):
        self.storage = _FakeStorage(chain)
        self._root_state_id = "root"
        self._current_state_id = chain[-1]["output_state_id"] if chain else "root"
        self.recorded = []

    def trace_step(self, func, func_name, raw_line, args, kwargs, targets):
        self.recorded.append(func_name)
        self._current_state_id = f"new{len(self.recorded)}"
        return func(*args, **kwargs)


def _stored(name, args, state, kwargs=None):
    pytest.importorskip("tracker")
    from tracker.runtime import _param_fingerprint

    return {"step_id": state, "func_name": name, "output_state_id": state,
            "param_fingerprint": _param_fingerprint(list(args), kwargs or {})}


def _double(x):
    return x * 2


def test_recorder_skips_calls_identical_to_the_latest_stored_step_of_that_name():
    chain = [_stored("_double", [1], "s1"), _stored("_double", [2], "s2")]
    rt = _FakeRT(chain)
    record, state_of = kit.analyst_recorder(rt, adapter=None)
    assert record(["y"], _double, 2) == 4  # the function still runs: the notebook needs its result
    assert rt.recorded == []
    assert state_of("y") == "s2"
    assert rt._current_state_id == "s2"  # new work goes after the end of the stored history


def test_recorder_records_a_call_that_differs_and_everything_after_it():
    chain = [_stored("_double", [1], "s1"), _stored("_double", [2], "s2")]
    rt = _FakeRT(chain)
    record, state_of = kit.analyst_recorder(rt, adapter=None)
    record(["y"], _double, 3)
    record(["z"], _double, 2)  # equal to the stored one, but the analyst has moved on: recorded
    assert rt.recorded == ["_double", "_double"]
    assert state_of("z") == "new2"


def test_recorder_records_everything_when_nothing_is_stored():
    rt = _FakeRT([])
    record, _ = kit.analyst_recorder(rt, adapter=None)
    record(["y"], _double, 1)
    assert rt.recorded == ["_double"]


def test_recorder_matches_each_stored_step_name_only_once_per_session():
    # a long argument (the tracker's fingerprint keeps 200 characters) must not make a later, changed call look stored
    chain = [_stored("_double", [2], "s2")]
    rt = _FakeRT(chain)
    record, _ = kit.analyst_recorder(rt, adapter=None)
    record(["y"], _double, 2)  # the reopened notebook runs its stored step again: not recorded
    record(["y"], _double, 2)  # the same name again is the analyst's own work: recorded
    assert rt.recorded == ["_double"]


def test_step_state_id_is_the_last_step_of_that_name_up_to_the_cursor():
    adapter = _Adapter({
        "s1": _Node("build_case_log", {}),
        "s2": _Node("initialize_log", {}),
        "s3": _Node("build_case_log", {}),
    })
    assert kit.step_state_id(adapter, None, "build_case_log") == "s3"
    assert kit.step_state_id(adapter, "s2", "build_case_log") == "s1"
    assert kit.step_state_id(adapter, "s1", "initialize_log") is None


# --- offers: more than one per case, and an offer as the case ---------------------------------------------------------------------


def offer_log() -> pd.DataFrame:
    t0 = pd.Timestamp("2016-01-01", tz="UTC")
    rows = [  # case, activity, EventID, OfferID
        ("c1", "A_Create", "Application_1", None),
        ("c1", "O_Create Offer", "Offer_1", None),
        ("c1", "O_Created", "OfferState_1", "Offer_1"),
        ("c1", "O_Create Offer", "Offer_2", None),
        ("c1", "O_Created", "OfferState_2", "Offer_2"),
        ("c1", "O_Accepted", "OfferState_3", "Offer_2"),
        ("c2", "A_Create", "Application_2", None),
        ("c2", "O_Create Offer", "Offer_3", None),
        ("c2", "O_Created", "OfferState_4", "Offer_3"),
    ]
    df = pd.DataFrame(rows, columns=[C, A, "EventID", "OfferID"])
    df[T] = [t0 + pd.Timedelta(minutes=i) for i in range(len(df))]
    return df


def test_complete_offer_ids_gives_create_offer_events_their_offer():
    ids = kit.complete_offer_ids(offer_log())
    assert ids.tolist() == [None, "Offer_1", "Offer_1", "Offer_2", "Offer_2", "Offer_2", None, "Offer_3", "Offer_3"]


def test_offers_per_case_counts_distinct_offers():
    per_case = kit.offers_per_case(offer_log())
    assert per_case.to_dict() == {"c1": 2, "c2": 1}


def test_offer_distribution_says_how_many_cases_have_each_number_of_offers():
    table = kit.offer_distribution(kit.offers_per_case(offer_log()))
    assert table["offers per case"].tolist() == [1, 2]
    assert table["cases"].tolist() == [1, 1]
    assert table["% of cases"].tolist() == [50.0, 50.0]


def test_offer_id_code_gives_every_offer_event_an_offer_id():
    log = offer_log()
    out = kit.enriched_log_from_code(log, None, kit.OFFER_ID_CODE)
    offer_events = out[out[A].str.startswith("O_")]
    assert offer_events["OfferID"].notna().all()  # O_Create Offer events now carry the id of their offer
    assert out.loc[out[A] == "O_Create Offer", "OfferID"].tolist() == ["Offer_1", "Offer_2", "Offer_3"]
    assert log["OfferID"].isna().sum() == 5  # the log the code ran on is left as it was


def test_enriched_log_from_code_is_none_when_the_code_defines_none():
    assert kit.enriched_log_from_code(offer_log(), None, "x = 1") is None


def test_offer_id_code_makes_the_path_by_offer_cover_all_offer_events():
    out = kit.to_lcm_log(kit.enriched_log_from_code(offer_log(), None, kit.OFFER_ID_CODE), "OfferID")
    assert out["case:concept:name"].value_counts().to_dict() == {"Offer_2": 3, "Offer_1": 2, "Offer_3": 2}


def test_to_lcm_log_can_use_another_attribute_as_the_case():
    out = kit.to_lcm_log(offer_log(), "OfferID")
    assert len(out) == 4  # only the events that have an OfferID; the O_Create Offer events have none
    assert out["case:concept:name"].nunique() == 3
    assert out["case:concept:name"].tolist() == ["Offer_1", "Offer_2", "Offer_2", "Offer_3"]


def test_path_attribute_options_are_the_attributes_that_group_events_into_cases():
    options = kit.path_attribute_options(offer_log())
    assert options[0] == C  # the case id comes first
    assert "OfferID" in options
    assert A not in options and T not in options  # the activity and the time do not identify a path
    assert "EventID" not in options  # unique per event: every path would be one event


def test_to_lcm_log_renames_the_case_activity_and_time_columns():
    out = kit.to_lcm_log(offer_log())
    assert list(out.columns) == ["case:concept:name", "concept:name", "time:timestamp"]
    assert len(out) == 9


# --- several notebooks saving to one course server ---------------------------------------------------------------------------------


def test_sync_url_names_the_notebook_in_the_address():
    assert kit.sync_url("https://sync.example.org/", "map-explorer") == "https://sync.example.org/n/map-explorer"


def test_session_folder_is_per_key_and_per_notebook():
    a = kit.session_folder("key-1", "map-explorer")
    assert a == kit.session_folder("key-1", "map-explorer")
    assert a != kit.session_folder("key-1", "initial-analysis")  # two notebooks with one key never share a folder
    assert a != kit.session_folder("key-2", "map-explorer")


def test_write_notebook_info_records_the_notebook_and_a_hash_of_its_file(tmp_path):
    notebook = tmp_path / "nb.py"
    notebook.write_text("print('hello')")
    folder = tmp_path / "prov"
    kit.write_notebook_info(folder, "map-explorer", notebook, version="1.0")
    info = json.loads((folder / "notebook.json").read_text())
    assert info["notebook"] == "map-explorer" and info["version"] == "1.0"
    assert info["sha256"] == hashlib.sha256(notebook.read_bytes()).hexdigest()


def test_write_notebook_info_still_writes_when_the_file_cannot_be_read(tmp_path):
    kit.write_notebook_info(tmp_path, "map-explorer", tmp_path / "missing.py")  # e.g. a hosted notebook that has no file on disk
    info = json.loads((tmp_path / "notebook.json").read_text())
    assert info["notebook"] == "map-explorer" and info["sha256"] is None
