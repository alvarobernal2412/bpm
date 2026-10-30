import pandas as pd
from typing import List, Tuple, Any


def init_value_of_tracking_method(tracking_method: str) -> Any:
    """Initialize the starting value for a tracking method."""
    # TODO: Check why this hardcoded value is in here
    HIGHFLOAT = 2000000.0
    match tracking_method:
        case 'latest':
            return None
        case 'count':
            return 0
        case 'sum':
            return 0
        case 'min':
            return HIGHFLOAT
        case 'append':
            return list()
        # TODO: Check whether I need a 'max' case since this is referenced in track_variables
        case _:
            raise ValueError(f'Tracking method "{tracking_method}" not supported')


def track_variables(
        log: pd.DataFrame,
        tracking_list: List[Tuple[str, str]],
        case_id_col: str = 'case:concept:name'
) -> pd.DataFrame:
    """
    Track variables across events in each case using specified methods.

    Args:
        log: Event log DataFrame
        tracking_list: List of (column_name, tracking_method) tuples
        case_id_col: Name of the case ID column

    Returns:
        Enhanced DataFrame with tracking columns
    """
    # Case History Aggregation: keep track of current state of a variable through history of a case
    value_store = {}  # map each tracked variable (incl method) and case to its current value
    added_cols = {}  # map each tracked variable (incl method) to a growing list/vector of values

    for (col, method) in tracking_list:
        added_cols[(col, method)] = []

    for index, row in log.iterrows():
        case_id = row[case_id_col]
        for (col, method) in tracking_list:
            if (case_id, col, method) not in value_store:
                value_store[(case_id, col, method)] = init_value_of_tracking_method(method)
            if not pd.isna(row[col]):
                match method:
                    case 'latest':
                        value_store[(case_id, col, method)] = row[col]
                    case 'count':
                        value_store[(case_id, col, method)] = value_store[(case_id, col, method)] + 1
                    case 'max':
                        value_store[(case_id, col, method)] = max(row[col], value_store[(case_id, col, method)])
                    case 'min':
                        value_store[(case_id, col, method)] = min(row[col], value_store[(case_id, col, method)])
                    case 'sum':
                        value_store[(case_id, col, method)] = round(value_store[(case_id, col, method)] + row[col], 2)
                    case 'append':
                        value_store[(case_id, col, method)].append(row[col])
                    case _:
                        raise ValueError(f'Update method "{method}" not supported')

            added_cols[(col, method)].append(value_store[(case_id, col, method)])

    for (col, method) in tracking_list:
        tracking_col_name = col + '::' + method
        log[tracking_col_name] = added_cols[(col, method)]

    return log


def create_case_log(
        event_log: pd.DataFrame,
        case_id_col: str = 'case:concept:name',
        timestamp_col: str = 'time:timestamp',
        activity_col: str = 'concept:name'
) -> pd.DataFrame:
    """
    Create an initial case log from an event log.

    Args:
        event_log: The event log DataFrame
        case_id_col: Name of the case ID column
        timestamp_col: Name of the timestamp column
        activity_col: Name of the activity column

    Returns:
        Case log DataFrame with start_time, end_time, no_of_events, and duration
    """
    cases = event_log.groupby(case_id_col)
    case_log = cases.agg(
        start_time=(timestamp_col, 'first'),
        end_time=(timestamp_col, 'last'),
        no_of_events=(activity_col, 'count')
    )
    case_log['duration'] = case_log['end_time'] - case_log['start_time']
    return case_log