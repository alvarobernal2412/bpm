import marimo as mo
import pandas as pd

SECONDS_PER_DAY = 86400.0


def timedelta_columns(df):
    return [col for col in df.columns if pd.api.types.is_timedelta64_dtype(df[col])]


def _format_days(value):
    """Render a float number of days the way the timedelta it came from rendered."""
    if pd.isna(value):
        return value
    return str(pd.Timedelta(days=float(value)).round('us'))


def enable_chart_builder():
    """Gives every table marimo's Visualize button (its chart builder) also when the notebook runs as an app.

    marimo offers it only in edit mode: its table plugin sets `show_chart_builder = app_mode == "edit"`. The button works in an
    app too (the chart is drawn in the browser from data the table already carries), so this makes the plugin see "edit" mode.
    It touches a private name of the pinned marimo, so it never raises: if marimo changes, tables simply keep their stock toolbar.
    Returns whether the switch was applied.
    """
    try:
        from marimo._plugins.ui._impl import table as table_plugin

        if not callable(getattr(table_plugin, "get_mode", None)):
            return False
        table_plugin.get_mode = lambda: "edit"
        return True
    except Exception:
        return False


def table(df, **kwargs):
    """mo.ui.table over df with timedelta columns rewritten as a number of days.

    Required for charting: Altair rejects timedelta64, which drops the table to
    marimo's CSV path where dotted headers ('a.b') get mangled to U+2024 and read as
    null, breaking charts that reference them. Cells still display as timedeltas via
    format_mapping.
    """
    converted = timedelta_columns(df)

    if converted:
        df = df.copy()
        for col in converted:
            df[col] = df[col].dt.total_seconds() / SECONDS_PER_DAY

        kwargs['format_mapping'] = {
            **{col: _format_days for col in converted},
            **kwargs.get('format_mapping', {}),
        }
        kwargs['header_tooltip'] = {
            **{col: 'Stored as a number of days, so it can be charted' for col in converted},
            **kwargs.get('header_tooltip', {}),
        }

    # match what marimo itself uses when a bare frame is rendered, so wrapping a
    # frame in this helper does not change how the tab looks
    kwargs.setdefault('selection', None)
    kwargs.setdefault('pagination', None)

    return mo.ui.table(df, **kwargs)
