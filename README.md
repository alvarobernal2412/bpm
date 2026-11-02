# BPI 2017, Task 1 on molab: analyst and reviewer

Two marimo notebooks that answer the three questions of the first exploratory task (the schema of `A_Create Application`,
its missing values, the attributes re-used across activities) with the maps of the
[Linear Continuous Process Mapper](https://github.com/alvarobernal2412/lc-maps) (the `lcm` library, installed from PyPI as `linear-continuous-process-mapper`), annotate them
with [`marimo-pmprov`](https://github.com/alvarobernal2412/marimo-pmprov) and record the analysis with
[`pmprov`](https://github.com/alvarobernal2412/pmprov).

| File | Mode | What it does |
|---|---|---|
| `analyst.py` | `analyst` | Runs the analysis, records every step, lets you **Pick** a map or table as the target of a note, write notes, edit them and **Export PDF**. |
| `reviewer.py` | `reviewer` | Opens the stored provenance **read-only**: step through the analysis, press **Replay** on a note to jump to its step. Maps and tables are restored as they were at that step. Nothing is recorded. |
| `data/bpi2017.parquet` | | The whole BPI Challenge 2017 log (31,509 applications, 1,202,267 events, 19 columns), 25 MB. A copy of `BPI_Challenge_2017.xes`. |
| `provenance/` | | Where the provenance is stored (`provenance.db` and `artifacts/`). Empty until `analyst.py` has run. |

Each notebook starts with a `# /// script` header that lists its dependencies, so molab (or `marimo --sandbox`) builds the
environment from it. Python 3.13 is needed (pmprov requires it).

## Open on molab

molab opens a notebook straight from a GitHub URL (the pattern comes from marimo's documentation; this repo has not been
opened on molab yet, see "Things to know"):

- analyst: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/analyst.py
- reviewer: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/reviewer.py

## Data

`data/bpi2017.parquet` is a Parquet copy of `BPI_Challenge_2017.xes`, the BPI Challenge 2017 event log:
van Dongen, B.F. (Boudewijn), *BPI Challenge 2017*, 4TU.ResearchData,
<https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b>. It stays under the terms of the original dataset; check
them on the dataset page before reusing it.

## What molab delivers

Opening a notebook from GitHub gives molab **only the notebook file**: the other files of the repository (`data/`,
`provenance/`) are not next to it (the first version of this repo failed with `No module named 'app'` for that reason, when the mapper was a folder here), and
`analyst.py` and `reviewer.py` do not share a file system. So each notebook brings in what it needs:

- The mapper is the `lcm` library: `analyst.py` lists `linear-continuous-process-mapper` in its dependency header, so molab installs it from PyPI.
- `analyst.py` looks for `data/` next to itself and, when it is not there, downloads it once from this
  repository (`https://github.com/alvarobernal2412/bpm/archive/refs/heads/main.zip`) into a temporary folder.
- The provenance travels as one file, `provenance.zip`: `analyst.py` has a **Download provenance.zip** button, and
  `reviewer.py` has a drop area for it (or it can be placed next to `reviewer.py`).

## Use

1. Open `analyst.py`, wait for the maps (about a minute for the first one), pick targets, write notes. The steps and notes are
   stored in a `provenance/` folder as you go.
2. Press **Download provenance.zip** in `analyst.py` before you close the notebook (a hosted notebook's files may not survive).
3. Open `reviewer.py` and drop `provenance.zip` into it, then step through the analysis and the notes.

On your own machine nothing needs downloading: keep the folder as it is, `provenance/` is created next to the notebooks and both
notebooks find it. `PMPROV_DIR` changes where it goes; if that folder cannot be written the notebook uses a temporary one.

## Doing it on molab and continuing locally

Download `provenance.zip` from the analyst on molab, unzip it into a `provenance/` folder next to the notebooks (or drop the
zip into the reviewer) and open either notebook.

pmprov stores the **absolute path** of every artifact file in `provenance.db`, so a downloaded history still points at molab's
folders. Both notebooks therefore re-point the stored artifacts at the `artifacts/` folder next to the database when they
start (`relocate_artifacts`, by file name). Tested by moving a stored history to a folder where its stored paths did not exist:
without the fix the notes and the tree load but no map or table can be restored; with it everything is restored. Keep
`provenance.db` and `artifacts/` together. The analyst notebook continues a downloaded history (same history name), the
reviewer only reads it.

## How steps are recorded

pmprov normally records a notebook by rewriting its cells, which needs marimo to be started with a patch
(`python -m provenance_widget.marimo_launcher`). molab starts marimo itself, so `analyst.py` records its steps explicitly:
every analysis step is run through `record(targets, function, *args)`, which calls pmprov's `trace_step`. The same notebook
also works when started with the launcher or with plain `marimo run`.

## Things to know

- **Tested locally**, with each notebook alone in an empty folder to imitate what molab delivers: `analyst.py` installed `lcm` from PyPI, downloaded
  `data/`, loaded the full log, rendered the 3 maps and 6 pickable targets, recorded its steps and produced
  `provenance.zip`; `reviewer.py`, in a folder with only itself and that zip (the original store deleted), restored the history,
  the note, the maps and the tables. Also against the released pmprov 0.10.0 and marimo-pmprov 0.2.4. The drop area of the
  reviewer could not be driven by the test tool (the zip is over its 10 MB limit); the same code path through a `provenance.zip`
  next to the notebook was tested. **Not tested on molab itself** beyond the failure that led to this version.
- The full analysis stores about 40 MB of artifacts. The zip is built in memory when you press the button.
- Maps in the exported PDF need `kaleido` and a Chrome in the environment; without them the notes and tables still export.
- `reviewer.py` needs a history named `BPI 2017 Task 1 with LCM maps`, which `analyst.py` creates.
- The download of `data/` follows `main` of this repository (not a fixed version), and needs internet access from the
  notebook.
