# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo>=0.25.2",
#     "pandas>=3.1.0",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd

    mo.md(f"""
    # Probe

    If you can read this, the notebook started in this mode. It has no data, no downloads and no helper modules: only marimo and
    pandas {pd.__version__}.
    """)
    return


if __name__ == "__main__":
    app.run()
