import pandas as pd
from typing import List, Tuple
from core.data.enrichment import track_variables, create_case_log
from core.constants import CASE_ID_COL, ACTIVITY_COL, TIMESTAMP_COL


class DataProcessor:
    """Handles all data transformation and preparation logic."""

    def __init__(self):
        pass

    def prepare_base_log(self, raw_log: pd.DataFrame) -> pd.DataFrame:
        """Prepare the base enriched log."""
        activity_tracking = (ACTIVITY_COL, "append")
        tracking_vars = [activity_tracking]
        return track_variables(raw_log, tracking_vars, CASE_ID_COL)

    def filter_by_activities(
        self, log: pd.DataFrame, selected_activities: List[str]
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Filter log to only include selected activities."""
        filtered_log = log[log[ACTIVITY_COL].isin(selected_activities)].copy()
        removed_cases = set(log[CASE_ID_COL]) - set(filtered_log[CASE_ID_COL])
        return filtered_log, list(removed_cases)

    def create_case_log_with_variants(
        self, filtered_log: pd.DataFrame, selected_activities: List[str], removed_cases: List[str], visualize_empty_cases: bool
    ) -> pd.DataFrame:
        """Create case-level log with sequential variants."""
        case_log = create_case_log(
            filtered_log,
            CASE_ID_COL,
            TIMESTAMP_COL,
            ACTIVITY_COL,
        )

        # Add sequential variant
        cases = filtered_log.groupby(CASE_ID_COL)
        seq_variant_col = f"{ACTIVITY_COL}::append"
        case_log["seq_variant"] = cases[seq_variant_col].last()
        case_log = case_log.dropna(subset=["seq_variant"])

        # Filter variants to only include selected activities
        case_log["seq_variant"] = case_log["seq_variant"].apply(
            lambda seq: [act for act in seq if act in selected_activities]
        )

        if visualize_empty_cases and removed_cases:
            # re-add removed cases with empty variants
            new_rows = pd.DataFrame(
                [[pd.NaT, pd.NaT, 0, pd.NaT, ["EMPTY TRACE"]] for _ in removed_cases],
                index=removed_cases,
                columns=case_log.columns,
            )
            case_log = pd.concat([case_log, new_rows])

        return case_log.copy()
