# lib

Helper modules of the initial-analysis notebooks (`01_initial-analysis.py`, `initial-review.py`).

- `temporal_characteristics_util.py`, `data_quality_util.py`, `display_util.py`, `attribute_util.py`, `structure_util.py`: copied
  unchanged from [hvoelzer/marimo-pm](https://github.com/hvoelzer/marimo-pm), the exploratory tool the notebooks are derived from.
- `initial_analysis_kit.py`: the analysis stages of the notebooks as plain functions (tested in `tests/`).

molab delivers only the notebook file, so a notebook that does not find this folder next to it downloads the modules from
`raw.githubusercontent.com/alvarobernal2412/bpm/main/lib/` and puts them on `sys.path`.
