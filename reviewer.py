# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.2",
#     "pmprov[duckdb,parquet,graph]>=0.10.0",
#     "marimo-pmprov[pdf]>=0.2.4",
#     "pandas>=3.1.0",
#     "plotly>=7.1.0",
#     "networkx>=3.7",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # BPI Challenge 2017, Task 1: Schemas (reviewer)

    The reviewer notebook. It opens the provenance that `analyst.py` recorded (the `provenance.zip` you download there)
    and **only reads it**: nothing is recorded and nothing can be edited. In the sidebar, step through the recorded analysis with the
    replay stepper, or press **Replay** on a note to jump to the step it was written at. The maps and tables below are
    restored as they were at the step you are on.

    Run `analyst.py` first and download its `provenance.zip`; until a history is loaded here there is nothing to review.
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import os as _os
    import tempfile as _tempfile
    from pathlib import Path

    from tracker.storage import DuckDBSQLiteBackend
    from tracker.runtime import RuntimeTracker
    from provenance_widget.pmprov_adapter import PmprovAdapter
    from provenance_widget.widget import ProvenancePanel

    def _folder_of_this_notebook():
        try:
            folder = Path(str(mo.notebook_location()))
            if folder.is_dir():
                return folder
        except Exception:
            pass
        return Path.cwd()

    HERE = _folder_of_this_notebook()

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

    def unpack_provenance(zip_bytes, target):
        """Unzip a `provenance.zip` into `target`, refusing any member that would land outside it."""
        import io
        import zipfile

        target = Path(target)
        target.mkdir(parents=True, exist_ok=True)
        root = target.resolve()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            for member in archive.infolist():
                destination = (root / member.filename).resolve()
                if destination != root and root not in destination.parents:
                    raise ValueError(f"unsafe path in the zip file: {member.filename}")
            archive.extractall(root)

    # Where the provenance is read from: ./provenance next to the notebook, or PMPROV_DIR; a temporary folder if that
    # one cannot be written (a read-only project).
    _wanted = Path(_os.environ.get("PMPROV_DIR") or HERE / "provenance")
    try:
        _wanted.mkdir(parents=True, exist_ok=True)
        PROVENANCE_DIR = _wanted
    except OSError:
        PROVENANCE_DIR = Path(_tempfile.mkdtemp(prefix="bpm-provenance-"))

    HISTORY_NAME = "BPI 2017 Task 1 with LCM maps"
    return (
        DuckDBSQLiteBackend,
        HISTORY_NAME,
        HERE,
        PROVENANCE_DIR,
        Path,
        PmprovAdapter,
        ProvenancePanel,
        RuntimeTracker,
        mo,
        relocate_artifacts,
        unpack_provenance,
    )


@app.cell(hide_code=True)
def _(mo):
    # A hosted notebook has its own files, so the provenance comes in as the zip file the analyst notebook offers.
    uploaded_provenance = mo.ui.file(filetypes=[".zip"], kind="area", label="Drop provenance.zip here")
    mo.vstack([
        mo.md(
            "**Provenance.** Download `provenance.zip` from `analyst.py` and drop it here (or put it next to this "
            "notebook). Dropping a file replaces the history that is loaded."
        ),
        uploaded_provenance,
    ])
    return (uploaded_provenance,)


@app.cell(hide_code=True)
def _(
    DuckDBSQLiteBackend,
    HISTORY_NAME,
    PROVENANCE_DIR,
    HERE,
    Path,
    RuntimeTracker,
    mo,
    relocate_artifacts,
    unpack_provenance,
    uploaded_provenance,
):
    # a zip dropped into the notebook, or a provenance.zip next to it, becomes the folder that is read
    if uploaded_provenance.value:
        unpack_provenance(uploaded_provenance.value[0].contents, PROVENANCE_DIR)
    elif not (PROVENANCE_DIR / "provenance.db").exists() and (HERE / "provenance.zip").exists():
        unpack_provenance((HERE / "provenance.zip").read_bytes(), PROVENANCE_DIR)

    mo.stop(
        not (PROVENANCE_DIR / "provenance.db").exists(),
        mo.callout(
            mo.md("No provenance loaded yet. Drop the `provenance.zip` from `analyst.py` above."),
            kind="warn",
        ),
    )

    # a history that was downloaded from another machine points at that machine's folders
    relocate_artifacts(PROVENANCE_DIR / "provenance.db", PROVENANCE_DIR / "artifacts")

    storage = DuckDBSQLiteBackend(
        db_path=PROVENANCE_DIR / "provenance.db", artifact_dir=PROVENANCE_DIR / "artifacts"
    )
    history_id = storage.find_latest_history_by_name(HISTORY_NAME)
    mo.stop(
        history_id is None,
        mo.callout(mo.md(f"The store has no history named `{HISTORY_NAME}`. Run `analyst.py` first."), kind="warn"),
    )

    # Resume the stored history without installing the kernel hooks of init_marimo(): the cells of this notebook
    # are not analysis steps and must not be added to the record.
    rt = RuntimeTracker.resume(storage, history_id, session_id="reviewer")
    return history_id, rt


@app.cell(hide_code=True)
def _(PmprovAdapter, ProvenancePanel, mo, rt):
    adapter = PmprovAdapter(rt)
    panel = ProvenancePanel(source=adapter, mode="reviewer")
    # build the tree now, not in the background, so the first snapshot below already knows its step
    panel.refresh()
    # every step of the stepper, and every Replay on a note, moves this cursor; cells that call get_cursor() re-run
    get_cursor = panel.reactive_cursor(mo.state)
    return adapter, get_cursor, panel


@app.cell(hide_code=True)
def _(mo, panel):
    # mo.sidebar(...) has to be the last bare expression of its cell to render
    mo.sidebar(panel.sidebar())
    return


@app.cell(hide_code=True)
def _(adapter, get_cursor, mo, panel):
    # the whole analysis at the step the reviewer is on (the latest one until they step), each variable as it was
    # bound then. There is no live analysis in this notebook, so the snapshot is always of a recorded step.
    snap = panel.snapshot(get_cursor() or adapter.latest_state_id())
    mo.callout(mo.md(snap.banner()), kind="info")
    return (snap,)


@app.cell(hide_code=True)
def _(mo, snap):
    _titles = {
        "create_schema": "1a. The schema of `A_Create Application`",
        "missing_values": "1b. Missing values in that schema",
        "attribute_reuse": "1c. Attributes re-used across activities",
    }
    _parts = []
    for _name, _title in _titles.items():
        _frame = snap.get(_name)
        _parts.append(mo.md(f"## {_title}"))
        _parts.append(
            mo.ui.table(_frame, selection=None, pagination=None) if _frame is not None else mo.md(snap.missing(_name))
        )
    mo.vstack(_parts)
    return


@app.cell(hide_code=True)
def _(mo, snap):
    _maps = {
        "application_figure": "The application states, set-based map",
        "offer_id_figure": "The events that carry `OfferID`",
        "credit_score_figure": "The events that carry `CreditScore`",
    }
    _parts = [mo.md("## Maps")]
    for _name, _title in _maps.items():
        _figure = snap.get(_name)
        _parts.append(mo.md(f"**{_title}**"))
        _parts.append(mo.as_html(_figure) if _figure is not None else mo.md(snap.missing(_name)))
    mo.vstack(_parts)
    return


if __name__ == "__main__":
    app.run()
