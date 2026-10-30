import pandas as pd
import networkx as nx
from typing import Dict, Any
from core.graph_builders import AbstractGraphBuilder


class GraphService:
    """Handles graph construction and simplification."""

    def __init__(self, graph_builders: Dict[str, AbstractGraphBuilder]):
        self.graph_builders = graph_builders

    def build_graph(
        self,
        case_log: pd.DataFrame,
        variant_col: str,
        builder_key: str,
        allow_loops: bool = True,
    ) -> nx.MultiDiGraph:
        builder = self.graph_builders.get(builder_key)
        if not builder:
            raise ValueError(f"Unknown graph builder: {builder_key}")
        return builder.build(case_log, variant_col, allow_loops=allow_loops)

    def simplify_graph(self, G: nx.MultiDiGraph, threshold: int) -> nx.MultiDiGraph:
        """Removes nodes with incoming weight below threshold."""
        G_simplified = G.copy()
        nodes_to_remove = []

        for node in G_simplified.nodes():
            incoming_weight = sum(
                G_simplified.edges[pred, node, key]["weight"]
                for pred in G_simplified.predecessors(node)
                for key in G_simplified[pred][node]
            )
            if incoming_weight < threshold:
                nodes_to_remove.append(node)

        for node in nodes_to_remove:
            G_simplified.remove_node(node)

        return G_simplified
