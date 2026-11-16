import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import xes_to_parquet as x  # noqa: E402

XES = """<?xml version="1.0" encoding="UTF-8" ?>
<log xes.version="2.0">
  <float key="meta_x" value="1.0"/>
  <trace>
    <string key="concept:name" value="Application_1"/>
    <string key="LoanGoal" value="Car"/>
    <float key="RequestedAmount" value="100.0"/>
    <event>
      <string key="concept:name" value="A_Create Application"/>
      <string key="lifecycle:transition" value="complete"/>
      <date key="time:timestamp" value="2016-01-01T20:51:15.304+11:00"/>
      <float key="OfferedAmount" value="5.5"/>
    </event>
    <event>
      <string key="concept:name" value="A_Submitted"/>
      <string key="lifecycle:transition" value="complete"/>
      <date key="time:timestamp" value="2016-01-01T20:52:00.000+11:00"/>
    </event>
  </trace>
  <trace>
    <string key="concept:name" value="Application_2"/>
    <event>
      <string key="concept:name" value="A_Create Application"/>
      <string key="lifecycle:transition" value="schedule"/>
      <date key="time:timestamp" value="2016-01-02T10:00:00.000+11:00"/>
    </event>
  </trace>
</log>
"""


def test_enrich_renames_colons():
    df = pd.DataFrame(columns=["case:concept:name", "concept:name", "time:timestamp", "lifecycle:transition"])
    out = x.enrich(df)
    assert not any(":" in c for c in out.columns)
    for name in ("case_concept_name", "concept_name", "time_timestamp", "lifecycle_transition"):
        assert name in out.columns


def test_enrich_adds_case_lifecycle():
    df = pd.DataFrame({"case:concept:name": ["Application_1"], "lifecycle:transition": ["complete"]})
    out = x.enrich(df)
    assert out["case_lifecycle"].tolist() == ["Application_1, complete"]
    assert not out["case_lifecycle"].isna().any()


def test_read_xes_small(tmp_path):
    path = tmp_path / "log.xes"
    path.write_text(XES, encoding="utf8")
    df = x.read_xes(str(path))
    assert len(df) == 3
    assert {"case:concept:name", "concept:name", "time:timestamp", "case:LoanGoal"} <= set(df.columns)
    assert "meta_x" not in df.columns
    assert str(df["time:timestamp"].dtype) == "datetime64[us, UTC]"
    assert df["case:LoanGoal"].tolist()[:2] == ["Car", "Car"] and pd.isna(df["case:LoanGoal"].iloc[2])
    assert df["OfferedAmount"].iloc[0] == 5.5
