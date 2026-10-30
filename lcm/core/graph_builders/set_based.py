import pandas as pd
import networkx as nx
from collections import defaultdict

from .abstract_graph_builder import AbstractGraphBuilder


class SetBasedPrefixGraphBuilder(AbstractGraphBuilder):
    def __init__(self, allow_loops: bool = True):
        self._allow_loops = allow_loops

    @property
    def name(self) -> str:
        return "Set-Based Prefix Graph"

    def build(
        self, case_log: pd.DataFrame, seq_variant_col: str, allow_loops: bool = True
    ) -> nx.MultiDiGraph:
        """
        Build a prefix graph from a case log
        """
        state_counts = defaultdict(int)
        transitions = []  # store each transition as (from_state, to_state, activity)

        for _, row in case_log.iterrows():
            activities = row[seq_variant_col]
            current_state = frozenset()
            state_counts[current_state] += 1

            for i, activity in enumerate(activities):
                new_state = frozenset(activities[: i + 1])
                if current_state != new_state or allow_loops:
                    transitions.append((current_state, new_state, activity))
                current_state = new_state
                state_counts[current_state] += 1

        G = nx.MultiDiGraph()
        # add nodes
        for state, count in state_counts.items():
            state_label = "START" if not state else "{" + ", ".join(sorted(state)) + "}"
            G.add_node(
                state, weight=count, label=state_label, activities_completed=len(state)
            )

        # group transitions by (from_state, to_state, activity) to count occurrences per activity
        transition_groups = defaultdict(int)
        for from_state, to_state, activity in transitions:
            key = (from_state, to_state, activity)
            transition_groups[key] += 1

        # add each unique (from, to, activity) as a separate edge
        for (from_state, to_state, activity), count in transition_groups.items():
            G.add_edge(
                from_state,
                to_state,
                weight=count,
                activity=activity,
            )

        return G
