import pandas as pd
import networkx as nx
from abc import ABC, abstractmethod


class AbstractGraphBuilder(ABC):
    """Abstract base class for all graph builder"""

    @abstractmethod
    def build(
        self, case_log: pd.DataFrame, seq_variant_col: str, allow_loops: bool = True
    ) -> nx.MultiDiGraph:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """User friendly name for the builder strategy"""
