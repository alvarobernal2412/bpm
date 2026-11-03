# BPI 2017, Task 1: a student notebook and a model solution

Two [marimo](https://marimo.io) notebooks on the BPI Challenge 2017 loan-application log. They answer the three questions of the
first exploratory task (the schema of `A_Create Application`, its missing values, the attributes re-used across activities) with
the maps of the [Linear Continuous Process Mapper](https://github.com/alvarobernal2412/lc-maps) (the `lcm` library, installed
from PyPI as `linear-continuous-process-mapper`), annotated with
[`marimo-pmprov`](https://github.com/alvarobernal2412/marimo-pmprov) and recorded with
[`pmprov`](https://github.com/alvarobernal2412/pmprov). The questions and the background of the log are in
[`assignment.md`](assignment.md).

| Notebook | For | What it does |
|---|---|---|
| [`student-notebook.py`](student-notebook.py) | students | Analyst only. The student enters their **key**, takes a first look at the log, explores it with the map tools, and writes notes on the tables and maps. Work is saved to the course server under the key and comes back on the next visit. No code to change, and no way to switch to the reviewer. |
| [`model-solution.py`](model-solution.py) | everyone, after their own attempt | Reviewer only. A tutorial that **replays** an annotated analysis of the same questions, read from the course server: step through it, press **Replay** on a note to jump to its step. Nothing can be changed and nothing is recorded. |

| File | |
|---|---|
| `bpm_kit.py` | The code both notebooks share: the analysis steps, the key box and how a step is recorded. |
| `data/bpi2017.parquet` | The whole log (31,509 applications, 1,202,267 events, 19 columns), 25 MB. A copy of `BPI_Challenge_2017.xes`. |
| `assignment.md` | The assignment: context, the three questions, how to work. |

Each notebook starts with a `# /// script` header that lists its dependencies, so molab (or `marimo --sandbox`) builds the
environment from it. Python 3.13 is needed (pmprov requires it).

## Open on molab

molab opens a notebook straight from a GitHub URL. For students, open the first one with **Run as app**:

- Student notebook: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/student-notebook.py
- Model solution: https://molab.marimo.io/github/alvarobernal2412/bpm/blob/main/model-solution.py

molab delivers **only the notebook file**. So each notebook downloads what else it needs from this repository when it starts
(`bpm_kit.py`, and the log), from `raw.githubusercontent.com/alvarobernal2412/bpm/main/`. That follows
`main`, not a fixed version, and needs internet access from the notebook. On your own machine, with the folder checked out,
nothing is downloaded.

## Students and keys

The student notebook asks for a key and keeps the student's work on the course server
([provenance-sync](https://github.com/alvarobernal2412/provenance-sync)), so it survives a closed page, a restarted kernel or a
recycled hosted notebook. Keys are made on the server's `/keys` page: create a course, add its students, copy their keys. The
instructor reads the work on the server's `/viewer` page, course by course.

`PMPROV_SYNC_URL` points the notebook at another server; set it to an empty value to work without one, and the work then stays in
`provenance/` next to the notebook.

## The model solution

The model solution is not a file of this repository. It is an analysis stored on the course server, in the course `tutorial`, as
the work of a student called `model-solution`. It was made like any student's work: with the tools of the student notebook (the
first look, the attributes of an activity, the map explorer), under that student's key, with notes written on the tables and maps.
Then the course was **closed**: after its closing time the server refuses every save and keeps what was saved, so the solution
cannot be overwritten, and anyone with the key can still read it. `model-solution.py` holds that key (it can only read), downloads
the work and replays it in the reviewer.

To change the solution: reopen the course on the server's `/keys` page, work in the student notebook with the model-solution key,
and close the course again. The stored work is kept in an old database file format that every DuckDB reads, because molab's DuckDB
is older than the one a recent pmprov writes. Work saved by a recent DuckDB may not open on molab until it is converted.

## How steps are recorded

pmprov normally records a notebook by rewriting its cells, which needs marimo to be started with a patch. molab starts marimo
itself, so the notebooks record their steps explicitly: every step goes through `record(targets, function, *args)`, which calls
pmprov's `trace_step` (`analyst_recorder` in `bpm_kit.py`). The notebook runs again from the top whenever a page is opened; that
run repeats the stored history from its first step, and those steps are not recorded a second time, so a returning student does not
collect duplicates. A step a student asks for (a click) is always recorded.

## Data

`data/bpi2017.parquet` is a Parquet copy of `BPI_Challenge_2017.xes`, the BPI Challenge 2017 event log:
van Dongen, B.F. (Boudewijn), *BPI Challenge 2017*, 4TU.ResearchData,
<https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b>. It stays under the terms of the original dataset; check
them on the dataset page before reusing it.

## Things to know

- **Tested locally**: both notebooks run; the model solution is fetched from the course server and replays its notes; the student notebook records its first
  look and every map a student asks for, a reload adds no duplicate steps, and with a local copy of the course server the key flow
  works, including restoring the work after the local folder was deleted. **Not yet tested on molab itself.**
- A student's `provenance.zip` (the download button) keeps every step, note, table and map and leaves out stored values over 500 kB
  (copies of the whole log), so it stays small. A step whose value was left out still shows in the reviewer; only that value cannot
  be restored there.
- Maps in an exported PDF need `kaleido` and a Chrome in the environment; without them the notes and tables still export.
