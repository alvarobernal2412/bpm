# BPI 2017, Task 1 on molab: analyst and reviewer

Two marimo notebooks that answer the three questions of the first exploratory task (the schema of `A_Create Application`,
its missing values, the attributes re-used across activities) with the maps of the
[Linear Continuous Process Mapper](https://github.com/aaronkurz/linear-continuous-process-mapper-marimo), annotate them
with [`marimo-pmprov`](https://github.com/alvarobernal2412/marimo-pmprov) and record the analysis with
[`pmprov`](https://github.com/alvarobernal2412/pmprov).

| File | Mode | What it does |
|---|---|---|
| `analyst.py` | `analyst` | Runs the analysis, records every step, lets you **Pick** a map or table as the target of a note, write notes, edit them and **Export PDF**. |
| `reviewer.py` | `reviewer` | Opens the stored provenance **read-only**: step through the analysis, press **Replay** on a note to jump to its step. Maps and tables are restored as they were at that step. Nothing is recorded. |
| `data/bpi2017.parquet` | | The whole BPI Challenge 2017 log (31,509 applications, 1,202,267 events, 19 columns), 25 MB. A copy of `BPI_Challenge_2017.xes`. |
| `lcm/` | | The `app` and `core` packages of the Linear Continuous Process Mapper, unchanged (MIT, see `lcm/README.md`). |
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

## Use

1. Open `analyst.py`, wait for the maps (about a minute for the first one), pick targets, write notes. The steps and notes are
   stored in `provenance/` as you go.
2. Open `reviewer.py` (in the same folder) to review them.

Where the provenance goes can be changed with the `PMPROV_DIR` environment variable. If the folder cannot be written, the
analyst notebook falls back to a temporary folder and says where.

## Doing it on molab and continuing locally

The provenance is a folder, so it can be downloaded and used on another machine: put the downloaded `provenance/` folder next
to the notebooks (replacing the local one) and open either notebook.

pmprov stores the **absolute path** of every artifact file in `provenance.db`, so a downloaded folder still points at molab's
folders. Both notebooks therefore re-point the stored artifacts at the `artifacts/` folder next to the database when they
start (`relocate_artifacts`, by file name). Tested by moving a stored history to a folder where its stored paths did not exist:
without the fix the notes and the tree load but no map or table can be restored; with it everything is restored. Keep
`provenance.db` and `artifacts/` together. The analyst notebook continues the downloaded history (same history name), the
reviewer only reads it.

## How steps are recorded

pmprov normally records a notebook by rewriting its cells, which needs marimo to be started with a patch
(`python -m provenance_widget.marimo_launcher`). molab starts marimo itself, so `analyst.py` records its steps explicitly:
every analysis step is run through `record(targets, function, *args)`, which calls pmprov's `trace_step`. The same notebook
also works when started with the launcher or with plain `marimo run`.

## Things to know

- **Tested** locally with plain `marimo run` (analyst: steps recorded, note linked to a table, PDF exported; reviewer: opened a
  history whose stored paths were Linux paths, tree, 7 notes, tables and maps restored) and against the released pmprov 0.10.0 and
  marimo-pmprov 0.2.4. **Not tested on molab itself.**
- The full analysis stores about 0.2 GB of artifacts (the largest are the maps' service objects, about 107 MB). Check the
  storage limit of your molab project.
- Maps in the exported PDF need `kaleido` and a Chrome in the environment; without them the notes and tables still export.
- `reviewer.py` needs a history named `BPI 2017 Task 1 with LCM maps`, which `analyst.py` creates.
