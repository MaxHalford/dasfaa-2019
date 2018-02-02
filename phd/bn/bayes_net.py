import itertools

import networkx as nx
import pandas as pd

from . import cpd


class BayesNet(nx.DiGraph):

    def __init__(self, edges):
        """

        Args:
            edges (list of tuples): list of two-valued tuples indicating the
                directed dependencies between the nodes. The nodes are guessed
                from the list of dependencies.
        """

        super().__init__()

        # Add the edges
        self.add_edges_from(edges)

    def update_cpds(self, df: pd.DataFrame):
        """Updates each node's CDP given the data in a pandas.DataFrame."""
        for node in self.nodes:
            parents = list(self.predecessors(node))
            self.node[node]['cdp'] = cpd.CPD(df=df, on=node, by=parents)

    def plot(self, ax):
        """Draws the DAG on a matplotlib.axis."""
        layout = nx.drawing.nx_agraph.graphviz_layout(self, prog='dot')
        nx.draw(
            self,
            layout,
            with_labels=True,
            ax=ax,
            **{
                'node_color': 'black',
                'node_size': 0,
                'width': 1,
            }
        )
