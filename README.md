# BPI 2017, Task 1 on molab: one notebook, two modes

`bpm.py` is a marimo notebook that answers the three questions of the first exploratory task (the schema of
`A_Create Application`, its missing values, the attributes re-used across activities) with the maps of the
[Linear Continuous Process Mapper](https://github.com/alvarobernal2412/lc-maps) (the `lcm` library, installed from PyPI as
`linear-continuous-process-mapper`), annotates them with [`marimo-pmprov`](https://github.com/alvarobernal2412/marimo-pmprov)
and records the analysis with [`pmprov`](https://github.com/alvarobernal2412/pmprov).

The same notebook runs in two modes:

| Mode | What it does |
|---|---|
| `analyst` | Runs the analysis, records every step, lets you **Pick** a map or table as the target of a note, write notes, edit them and **Export PDF**. |
| `reviewer` | Opens the stored provenance **read-only**: step through the analysis, press **Replay** on a note to jump to its step (the maps and tables are restored as they were at that step, and the element the note is about is highlighted). Nothing is recorded, and the analysis is not run. |

| File | |
|---|---|
| `bpm.py` | The notebook. |
| `data/bpi2017.parquet` | The whole BPI Challenge 2017 log (31,509 applications, 1,202,267 events, 19 columns), 25 MB. A copy of `BPI_Challenge_2017.xes`. |
| `provenance/` | Where the provenance is stored (`provenance.db` and `artifacts/`). Empty until an analyst session has run. |

The notebook starts with a `# /// script` header that lists its dependencies, so molab (or `marimo --sandbox`) builds the
environment from it. Python 3.13 is needed (pmprov requires it).

## Choosing the mode

- **Before the run** (the usual way on your own machine): `marimo run bpm.py -- --mode reviewer`, or set `PMPROV_MODE=reviewer`
  (`analyst` likewise). The notebook then shows no switch.
- **In the notebook** (when it was not chosen before the run, such as on molab, which starts the notebook itself): a **Mode**
  switch at the top, analyst by default, that you can flip at any time.

Without a mode given the notebook starts as analyst, and an analyst session adds its steps to the stored history each time the
analysis runs.

## Open on molab

molab opens a notebook straight from a GitHub URL (the pattern comes from marimo's documentation):

https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/bpm.py

## Data

`data/bpi2017.parquet` is a Parquet copy of `BPI_Challenge_2017.xes`, the BPI Challenge 2017 event log:
van Dongen, B.F. (Boudewijn), *BPI Challenge 2017*, 4TU.ResearchData,
<https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b>. It stays under the terms of the original dataset; check
them on the dataset page before reusing it.

## What molab delivers

Opening a notebook from GitHub gives molab **only the notebook file**: the other files of the repository (`data/`, `provenance/`)
are not next to it, and what one session writes is not there in another. So the notebook brings in what it needs:

- The mapper is the `lcm` library, listed in the dependency header, so molab installs it from PyPI.
- In analyst mode the notebook looks for `data/` next to itself and, when it is not there, downloads it once from this
  repository (`https://github.com/alvarobernal2412/bpm/archive/refs/heads/main.zip`) into a temporary folder.
- The provenance travels as one file, `provenance.zip`: analyst mode has a **Download provenance.zip** button, and reviewer
  mode has a drop area for it (or it can be placed next to `bpm.py`).

## Use

1. Open `bpm.py` as analyst, wait for the maps (about a minute for the first one), pick targets, write notes. The steps and notes
   are stored in a `provenance/` folder as you go.
2. Press **Download provenance.zip** before you close the notebook (a hosted notebook's files may not survive).
3. Open `bpm.py` as reviewer (switch the mode, or start it with `--mode reviewer`) and drop `provenance.zip` into it, then step
   through the analysis and the notes.

On your own machine nothing needs downloading: keep the folder as it is and `provenance/` is created next to the notebook.
`PMPROV_DIR` changes where it goes; if that folder cannot be written the notebook uses a temporary one.

## Doing it on molab and continuing locally

Download `provenance.zip` on molab, unzip it into a `provenance/` folder next to `bpm.py` (or drop the zip into reviewer mode)
and open the notebook in either mode.

pmprov stores the **absolute path** of every artifact file in `provenance.db`, so a downloaded history still points at molab's
folders. The notebook therefore re-points the stored artifacts at the `artifacts/` folder next to the database when it starts
(`relocate_artifacts`, by file name). Keep `provenance.db` and `artifacts/` together. Analyst mode continues a downloaded history
(same history name), reviewer mode only reads it.

## How steps are recorded

pmprov normally records a notebook by rewriting its cells, which needs marimo to be started with a patch
(`python -m provenance_widget.marimo_launcher`). molab starts marimo itself, so the notebook records its steps explicitly:
every analysis step is run through `record(targets, function, *args)`, which calls pmprov's `trace_step`. The same notebook
also works when started with the launcher or with plain `marimo run`.

## Things to know

- **Tested locally**, with the notebook alone in an empty folder to imitate what molab delivers: analyst mode installed `lcm`
  from PyPI, downloaded `data/`, loaded the full log, rendered the maps and pickable targets and recorded its steps; reviewer
  mode (started with `--mode reviewer`) restored the history, the notes, the maps and the tables, and Replay highlighted the
  note's target. The in-notebook switch was flipped from analyst to reviewer in the same session. The drop area of reviewer
  mode could not be driven by the test tool (the zip is over its 10 MB limit); the same code path through a `provenance.zip`
  next to the notebook was tested. **Not tested on molab itself** beyond what led to this version.
- The full analysis stores about 45 MB of artifacts, but `provenance.zip` is about 1 MB: it keeps every step, note, table and
  map and leaves out stored values over 2 MB (copies of the whole log), so a long session stays small. A step whose value was
  left out still shows in reviewer mode; only that value cannot be restored there.
- Maps in the exported PDF need `kaleido` and a Chrome in the environment; without them the notes and tables still export.
- Reviewer mode needs a history named `BPI 2017 Task 1 with LCM maps`, which analyst mode creates.
- The download of `data/` follows `main` of this repository (not a fixed version), and needs internet access from the notebook.
