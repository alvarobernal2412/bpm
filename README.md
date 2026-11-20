# BPI 2017 and Dhana loan applications: course notebooks

[marimo](https://marimo.io) notebooks. The LC maps ones teach and assess the reading of linear continuous process maps (the
[`lcm`](https://github.com/alvarobernal2412/lc-maps) library, installed from PyPI as `linear-continuous-process-mapper`), with annotations
written in the [`marimo-pmprov`](https://github.com/alvarobernal2412/marimo-pmprov) side panel and steps recorded with
[`pmprov`](https://github.com/alvarobernal2412/pmprov). The tasks and the background of the log are in [`assignment.md`](assignment.md).

There are two sets of notebooks. The **LC maps** set (BPI 2017, Tasks 8 to 10: `tutorial.py`, `lcmap-notebook-analysis.py`, `lcmap-notebook-review.py`, `model-solution.py`) teaches and assesses the reading of process maps. The **initial analysis** set (`01_initial-analysis.py`, `initial-review.py`) lets students explore one event log, the enriched Dhana LoanApplication log, before any process mining analysis.

| Notebook | Panel mode | What it does |
|---|---|---|
| [`tutorial.py`](tutorial.py) | reviewer | Replays a recorded, annotated analysis of the workflow activities (`W_`) of the BPI 2017 log that demonstrates how to read the maps (mainstream vs. exceptional behavior, leakage, rework, folding, variants, the abstractions), with a reference of the map elements and settings, a guide to writing intents and findings, and a live map explorer. |
| [`lcmap-notebook-analysis.py`](lcmap-notebook-analysis.py) | analyst | The student enters a **key**, looks at the log, draws maps with the map explorer (every map is a recorded step) and writes annotations. Work is saved to the course server under the key. |
| [`lcmap-notebook-review.py`](lcmap-notebook-review.py) | reviewer | The reviewer enters a **student's key** and sees that student's work from the student notebook (steps, maps, annotations) replayed, with the same live map explorer. The work is only read, never saved. |
| [`model-solution.py`](model-solution.py) | reviewer | Replays the annotated solution of Tasks 8 to 10, with a live map explorer on the BPI 2017 log. |
| [`01_initial-analysis.py`](01_initial-analysis.py) | analyst | The student enters a **key** and explores the Dhana LoanApplication log, already loaded: log initialization (time zone, granularity, time frame, mandatory columns, global ordering), granularity and ordering analysis, the events view (global and local attributes, case inspection, case log with a code box to enrich it, raw events) and the activity schemas. Every choice is a recorded step, tables can be anchored and annotated in the side panel, and the annotations can be exported as a PDF. Work is saved to the course server under the key. |
| [`initial-review.py`](initial-review.py) | reviewer | The reviewer enters a **student's key** and sees that student's work from `01_initial-analysis.py` replayed step by step: the choices they made, the tables at each step and their annotations. The work is only read, never saved. |
| [`02_map-explorer.py`](02_map-explorer.py) | analyst | The student enters a **key** and draws linear continuous process maps of the Dhana LoanApplication log with the map explorer. *Each path is* chooses the attribute whose values make up a path: the case id, or another attribute such as `OfferID` (one path per offer). Every map is a recorded step and can be anchored and annotated. |
| [`00_lecture.py`](00_lecture.py) | none | The initial analysis for a lecture, as a plain marimo notebook: nothing is recorded and no key is needed. The first thing a student does is choose one of two event logs (Sepsis cases, `.xes`; Purchasing example, `.csv`), which are read in the format they came in. The rest is the same as `01_initial-analysis.py`. |

In all the LC maps notebooks the map explorer offers the same settings: activities (with quick selection by family), abstraction
(set-, last-activity- or sequence-based), up to three activity folds, self-loops, empty traces, and, for BPI 2017, whether a path is a
loan application or an offer (sub-tracing by `OfferID`). In the two reviewer notebooks of that set, **Open in the map explorer** below a
replayed map copies its settings into the explorer.

| File | |
|---|---|
| `bpm_kit.py` | The code the notebooks share: loading the logs, drawing a map, the map controls, the key box, recording a step and opening a recorded analysis. |
| `build_histories.py` | Records the tutorial and the model solution (steps and annotations) and writes them to `histories/`; with `--push`, also stores them on the course server. |
| `histories/tutorial.zip`, `histories/model-solution.zip` | The recorded analyses, replayed when the course server does not provide them. |
| `data/bpi2017.parquet` | BPI Challenge 2017 (31,509 applications, 1,202,267 events, 19 columns), 25 MB. |
| `data/dhana-loan-application.parquet` | The enriched Dhana LoanApplication log (20,343 applications, 761,372 events, 20 columns), 12 MB: colons in column names replaced by underscores (`time:timestamp` is `time_timestamp`) and a `case_lifecycle` column (`Application_652823628, complete`). |
| `lib/` | The helper modules of the initial-analysis notebooks (`initial_analysis_kit.py`: the analysis stages as functions; the exploration utilities from [marimo-pm](https://github.com/hvoelzer/marimo-pm)). See [`lib/README.md`](lib/README.md). |
| `data/SepsisCases2020EventLog.xes`, `data/Purchasing-Example.csv` | The two event logs of `00_lecture.py`, as they came in (Sepsis cases: 1,050 cases, 15,214 events; Purchasing example: 608 cases, 9,119 events). |
| `scripts/xes_to_parquet.py` | Converts an XES log to the enriched parquet: `python -I scripts/xes_to_parquet.py <log.xes> <out.parquet>`. |
| `tests/` | `pytest tests` (needs pandas, pyarrow, pytz; the recorder tests also need pmprov). |

Each notebook starts with a `# /// script` header that lists its dependencies, so molab (or `marimo --sandbox`) builds the
environment from it. Python 3.13 is needed (pmprov requires it).

## Saving to the course server

Each notebook that saves work has an identifier (`initial-analysis`, `map-explorer`) and saves to `<server>/n/<identifier>`, so a
student's work is kept per notebook on the course server (course > student > notebook). Next to the work, the notebook saves a small
`notebook.json` with its identifier and a hash of its file, so that the server knows which version of the notebook made each saved
revision. The LC maps notebooks still save to the server's older address, which is the notebook `default`. This needs a version of
[provenance-sync](https://github.com/alvarobernal2412/provenance-sync) with notebook addresses.

## If something goes wrong

Tell students the following. Most problems come from the notebook's session ending (the server restarted, the laptop went to sleep,
the connection dropped), and a reload fixes them:

- **marimo shows a red message** such as "Failed to fetch", "Failed update value", "Unauthorized" or a lost connection, or the page stops
  responding: **reload the page.** The key is remembered on that computer (unless "Remember on this computer" was unticked), and
  the work comes back as it was left: the choices, the maps and the annotations. If the key is asked for again, paste it again.
- **molab says "Failed to launch application" (or "kernel not found") in the app view.** Open the same notebook with **Edit** and run it
  there: that starts even when the app view does not. We saw this with the lecture notebook and with a probe notebook that only
  shows one line of text, so it comes from molab's app view, not from the notebooks or the event logs. molab's guide says an app
  is started from the share button of a running notebook ("Run as app"), and that an idle notebook is shut down after 90 minutes.
- **"Not saved to the course server yet"** appears while the first save is on its way; if the course server cannot be reached, the work
  stays on the computer and is saved when it can.
- **The map explorer is slow or the page freezes.** It starts on the 5 most frequent activities. Drawing every activity (25 in this log)
  makes a map of hundreds of nodes that takes about ten seconds and is heavy for the browser: choose fewer activities. Closing other
  notebook tabs and heavy programs helps too.
- **"None of the selected activities occurs…"** after choosing another attribute for *Each path is*: the message lists the activities that
  do occur under that choice; select some of them and press *Refresh visualization*.
- **"The key was not accepted"**: check that the key was pasted completely, or ask the instructor.

## Open on molab

- Tutorial: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/tutorial.py
- LC maps, student notebook: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/lcmap-notebook-analysis.py
- Model solution: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/model-solution.py
- LC maps, reviewer notebook (needs a student's key): https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/lcmap-notebook-review.py
- Initial analysis: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/01_initial-analysis.py
- Initial analysis, reviewer notebook (needs a student's key): https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/initial-review.py
- Map explorer: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/02_map-explorer.py

molab delivers only the notebook file, so each notebook downloads what else it needs (`bpm_kit.py`, `lib/`, a log, a recorded history)
from `raw.githubusercontent.com/alvarobernal2412/bpm/main/`. On your own machine, with the folder checked out, nothing is
downloaded.

## The recorded analyses

The tutorial and the model solution are made by `build_histories.py` with the same functions as the student notebook, so they
replay exactly like a student's work. The numbers in their annotations are computed from the logs by the script. To change an annotation, edit
the script and run it again:

```bash
python build_histories.py                                   # writes histories/*.zip
TUTORIAL_KEY=... SOLUTION_KEY=... python build_histories.py --push   # also stores them on the course server
```

A reviewer notebook first asks the course server (with the read key in `BPM_TUTORIAL_KEY` or `BPM_SOLUTION_KEY`, or the key
written in the notebook) and falls back to the zip in the repository. Both analyses are stored in the course `tutorial` as two
students (`tutorial` holds the tutorial, `model-solution` the model solution). The keys are in the notebooks on purpose:
once the course is closed they can only read. To change an analysis, reopen the course on the server's `/keys` page, push with its
key, then close the course so that the analysis cannot be overwritten. `build_histories.py` writes the database in DuckDB's oldest storage format, because molab's DuckDB is older than the
one a recent pmprov installs and refuses files written by a newer one.

## Annotations

The kind of an annotation is a tag: `intent` (what a map is for) or `finding` (what it shows). Further tags group the annotations: the task
(`task8`, `task9`, `task10`) in the model solution and in student work, the pattern (`rework`, `leakage`, ...) in the tutorial. An annotation's
tags belong to that annotation alone (marimo-pmprov 0.4.5 or later; pmprov itself keeps tags per step, so the adapter stores each annotation's
tags beside the database).

## Data

`data/bpi2017.parquet`: van Dongen, B.F., *BPI Challenge 2017*, 4TU.ResearchData,
<https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b>.
It stays under the terms of the original dataset.

`data/dhana-loan-application.parquet` is made from the *Dhana LoanApplication* XES log, a selection of the BPI Challenge 2017 log
(20,343 of its applications, filed in 2016). It stays under the terms of the original dataset.

`data/SepsisCases2020EventLog.xes`: Mannhardt, F., *Sepsis Cases - Event Log*, 4TU.ResearchData, <https://doi.org/10.4121/uuid:915d2bfb-7e84-49ad-a286-dc35f063a460>.
Both logs stay under the terms of the original datasets.
