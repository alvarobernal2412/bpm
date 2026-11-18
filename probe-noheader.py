import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    mo.md("""
    # Probe without a header

    If you can read this, the notebook started in this mode. It has no dependency header at all, no data, no downloads and no helper
    modules: only marimo.
    """)
    return


if __name__ == "__main__":
    app.run()
