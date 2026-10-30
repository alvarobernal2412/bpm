import pandas as pd
from core.constants import ALLOW_LOOPS
from core.data.data_processor import DataProcessor
from core.services.process_analytics_service import ProcessAnalyticsService
from core.services.graph_service import GraphService
from core.domain.graph_analyzer import GraphAnalyzer
from core.graph_builders import (
    SetBasedPrefixGraphBuilder,
    SequenceBasedPrefixTreeBuilder,
    LastActivityBasedGraphBuilder,
)


def create_process_analytics_service(
    event_log: pd.DataFrame,
) -> ProcessAnalyticsService:

    # Data layer
    data_processor = DataProcessor()

    # Graph layer
    graph_builders = {
        "set_based": SetBasedPrefixGraphBuilder(allow_loops=ALLOW_LOOPS),
        "sequence_based": SequenceBasedPrefixTreeBuilder(allow_loops=ALLOW_LOOPS),
        "last_activity_based": LastActivityBasedGraphBuilder(allow_loops=ALLOW_LOOPS),
    }
    graph_service = GraphService(graph_builders)
    graph_analyzer = GraphAnalyzer()

    return ProcessAnalyticsService(
        event_log=event_log,
        data_processor=data_processor,
        graph_service=graph_service,
        graph_analyzer=graph_analyzer,
    )
