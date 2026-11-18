# /// script
# dependencies = [
#     "marimo",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    mo.md("""
    # Probe without versions

    If you can read this, the notebook started in this mode. Its header declares only `marimo`, with no version, no Python version
    and no other package. It has no data, no downloads and no helper modules.
    """)
    return


if __name__ == "__main__":
    app.run()
