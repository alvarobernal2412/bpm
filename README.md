# BPI 2017, Tasks 8 to 10: a tutorial, a student notebook and a model solution

Three [marimo](https://marimo.io) notebooks that teach and assess the reading of linear continuous process maps (the
[`lcm`](https://github.com/alvarobernal2412/lc-maps) library, installed from PyPI as `linear-continuous-process-mapper`), with notes
written in the [`marimo-pmprov`](https://github.com/alvarobernal2412/marimo-pmprov) side panel and steps recorded with
[`pmprov`](https://github.com/alvarobernal2412/pmprov). The tasks and the background of the log are in [`assignment.md`](assignment.md).

| Notebook | Panel mode | What it does |
|---|---|---|
| [`tutorial.py`](tutorial.py) | reviewer | Replays a recorded, annotated analysis of a small log (BPIC 2020 *Domestic Declarations*) that demonstrates each pattern of the LCM paper (mainstream vs. exceptional behavior, knockout structure, leakage, rework, folding, outcome distribution, variants), with a reference of the map elements and settings, a guide to writing intents and findings, and a live map explorer. |
| [`student-notebook.py`](student-notebook.py) | analyst | The student enters a **key**, looks at the log, draws maps with the map explorer (every map is a recorded step) and writes notes. Work is saved to the course server under the key. |
| [`model-solution.py`](model-solution.py) | reviewer | Replays the annotated solution of Tasks 8 to 10, with a live map explorer on the BPI 2017 log. |

In all three notebooks the map explorer offers the same settings: activities (with quick selection by family), abstraction
(set-, last-activity- or sequence-based), up to three activity folds, self-loops, empty traces, and, for BPI 2017, whether a path is a
loan application or an offer (sub-tracing by `OfferID`). In the two reviewer notebooks, **Open in the map explorer** below a
replayed map copies its settings into the explorer.

| File | |
|---|---|
| `bpm_kit.py` | The code the notebooks share: loading the logs, drawing a map, the map controls, the key box, recording a step and opening a recorded analysis. |
| `build_histories.py` | Records the tutorial and the model solution (steps and notes) and writes them to `histories/`; with `--push`, also stores them on the course server. |
| `histories/tutorial.zip`, `histories/model-solution.zip` | The recorded analyses, replayed when the course server does not provide them. |
| `data/bpi2017.parquet` | BPI Challenge 2017 (31,509 applications, 1,202,267 events, 19 columns), 25 MB. |
| `data/declarations.csv` | BPI Challenge 2020, Domestic Declarations, preprocessed subset (8,260 cases, 46,375 events), from the `lc-maps` repository. |

Each notebook starts with a `# /// script` header that lists its dependencies, so molab (or `marimo --sandbox`) builds the
environment from it. Python 3.13 is needed (pmprov requires it).

## Open on molab

- Tutorial: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/tutorial.py
- Student notebook: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/student-notebook.py
- Model solution: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/model-solution.py

molab delivers only the notebook file, so each notebook downloads what else it needs (`bpm_kit.py`, a log, a recorded history)
from `raw.githubusercontent.com/alvarobernal2412/bpm/main/`. On your own machine, with the folder checked out, nothing is
downloaded.

## The recorded analyses

The tutorial and the model solution are made by `build_histories.py` with the same functions as the student notebook, so they
replay exactly like a student's work. The numbers in their notes are computed from the logs by the script. To change a note, edit
the script and run it again:

```bash
python build_histories.py                                   # writes histories/*.zip
TUTORIAL_KEY=... SOLUTION_KEY=... python build_histories.py --push   # also stores them on the course server
```

A reviewer notebook first asks the course server (with the read key in `BPM_TUTORIAL_KEY` or `BPM_SOLUTION_KEY`, or the key
written in the notebook) and falls back to the zip in the repository. Both analyses are stored in the course `tutorial` as two
students (`model-solution-2` holds the tutorial, `model-solution` the model solution). The keys are in the notebooks on purpose:
once the course is closed they can only read. To change an analysis, reopen the course on the server's `/keys` page, push with its
key, then close the course so that the analysis cannot be overwritten. `build_histories.py` writes the database in DuckDB's oldest storage format, because molab's DuckDB is older than the
one a recent pmprov installs and refuses files written by a newer one.

## Notes

The kind of a note is a tag: `intent` (what a map is for) or `finding` (what it shows). Further tags group the notes: the task
(`task8`, `task9`, `task10`) in the model solution and in student work, the pattern (`rework`, `leakage`, ...) in the tutorial. A note's
tags belong to that note alone (marimo-pmprov 0.4.5 or later; pmprov itself keeps tags per step, so the adapter stores each note's
tags beside the database).

## Data

`data/bpi2017.parquet`: van Dongen, B.F., *BPI Challenge 2017*, 4TU.ResearchData,
<https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b>.
`data/declarations.csv`: van Dongen, B.F., *BPI Challenge 2020: Domestic Declarations*, 4TU.ResearchData,
<https://doi.org/10.4121/uuid:3f422315-ed9d-4882-891f-e180b5b4feb5>, licensed CC BY-NC 4.0.
Both stay under the terms of the original datasets.
