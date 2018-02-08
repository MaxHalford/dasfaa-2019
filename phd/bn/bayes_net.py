import itertools
import re

import networkx as nx
import pandas as pd

from . import cpd


class BayesNet(nx.DiGraph):

    def __init__(self, nodes=[], edges=[]):
        """

        Args:
            nodes (list of str)
            edges (list of tuples): list of two-valued tuples indicating the
                directed dependencies between the nodes. Nodes are deduced from
                the list of dependencies if they are not specified in the list
                of nodes.
        """

        super().__init__()

        # Add the nodes
        self.add_nodes_from(nodes)

        # Add the edges
        self.add_edges_from(edges)

    def __str__(self):

        def concat(node):
            return str(self.node[node]['cpd']) + ''.join([concat(n) for n in self.successors(node)])

        return concat(self.root())

    def __repr__(self):
        return str(self)

    def root(self):
        """Returns the network's root node."""

        root = None

        def find_root(graph, node):
            predecessor = next(self.predecessors(node), None)
            if predecessor:
                root = find_root(graph, predecessor)
            else:
                root = node
            return root

        return find_root(self, list(self.nodes)[0])

    def steiner_tree(self, nodes):
        """Returns the minimal part of the tree that contains a set of nodes."""
        nodes = list(nodes)
        sub_nodes = set()

        def walk(node, path):

            if len(nodes) == 0:
                return

            if node in nodes:
                sub_nodes.update(path + [node])
                nodes.remove(node)

            for child in self.successors(node):
                walk(child, path + [node])

        walk(self.root(), [])

        sub_graph = self.subgraph(sub_nodes)
        sub_tree = BayesNet()
        for node in sub_graph.nodes:
            sub_tree.add_node(node, **sub_graph.node[node])
        sub_tree.add_edges_from(sub_graph.edges)

        return sub_tree

    def update_cpds(self, df: pd.DataFrame, n_most_common: int, n_bins: int):
        """Updates each node's CDP given the data in a pandas.DataFrame."""
        for node in self.nodes:
            self.node[node]['cpd'] = cpd.CPD(
                on=node,
                by=next(self.predecessors(node), None),
                n_most_common=n_most_common,
                n_bins=n_bins
            )
            self.node[node]['cpd'].build_from_df(df)

    def infer(self, query) -> float:

        # Map each variable to it's associated query
        queries = query.lower().split(' and ')
        queries = {re.split(' (==|in) ', query)[0]: query for query in queries}

        # Extract the part of the tree that contains the concerned variables and the root
        sub_tree = self.steiner_tree(queries.keys(), copy=True)

        # Extract the tree's root
        root = self.root()

        def subset_cpd(node):

            for variable, query in queries.items():
                if variable in sub_tree.node[node]['cpd'].index.names:
                    sub_tree.node[node]['cpd'] = sub_tree.node[node]['cpd'].query(query)

            for child in sub_tree.successors(node):
                subset_cpd(child)

        subset_cpd(root)

        def propagate(node, condition):

            cpd = (
                sub_tree.node[node]['cpd'].query(condition)
                if condition
                else sub_tree.node[node]['cpd']
            )

            if sub_tree.out_degree(node) == 0:
                return cpd.sum()

            proba = 0

            for att, p in cpd.iteritems():
                att = att[-1] if isinstance(att, tuple) else att
                proba += p * sum([
                    propagate(child, '{} == "{}"'.format(node, att))
                    for child in sub_tree.successors(node)
                ])

            return proba

        sel = propagate(root, None)

        return sel

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
