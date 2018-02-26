import itertools
import re

import networkx as nx
import pandas as pd

from phd import operator
from phd import tools

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

        def to_p(node, parent):
            return 'P({}|{})'.format(node, parent) if parent else 'P({})'.format(node)

        def concat(node, parent):
            return to_p(node, parent) + ''.join([concat(child, node) for child in self.successors(node)])

        return concat(self.root(), None)

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

    def update_cpds(self, df: pd.DataFrame, n_mcv: int, n_bins: int):
        """Updates each node's CDP given the data in a pandas.DataFrame."""
        for node in self.nodes:
            self.node[node]['cpd'] = cpd.CPD(
                on=node,
                by=next(self.predecessors(node), None),
                n_mcv=n_mcv,
                n_bins=n_bins
            )
            self.node[node]['cpd'].build_from_df(df)

    def infer(self, conditions) -> float:

        sub_tree = self.steiner_tree(conditions.keys())
        root = sub_tree.root()

        def subset_cpd(node):

            on = sub_tree.node[node]['cpd'].on
            by = sub_tree.node[node]['cpd'].by

            sub_tree.node[node]['cpd'] = sub_tree.node[node]['cpd'].subset(on, conditions.get(on))
            sub_tree.node[node]['cpd'] = sub_tree.node[node]['cpd'].subset(by, conditions.get(by))

            if sub_tree.out_degree(node) == 0 and by:
                return operator.In(set(sub_tree.node[node]['cpd'].index.get_level_values(by)))

            sub_conditions = [subset_cpd(child) for child in sub_tree.successors(node)]
            for condition in sub_conditions:
                sub_tree.node[node]['cpd'] = sub_tree.node[node]['cpd'].subset(on, condition)

            if by:
                return operator.In(set(sub_tree.node[node]['cpd'].index.get_level_values(by)))

        subset_cpd(root)

        def propagate(node, parent_interval=None):

            # Get the node's CPD
            cpd = sub_tree.node[node]['cpd']

            # Filter the CPD based on the parent's value
            if parent_interval:
                cpd = cpd.subset(cpd.by, operator.Equal(parent_interval))

            proba = 0

            for interval, p in cpd.iteritems():

                # Unpack the conditional and observed intervals
                by_interval, on_interval = interval if cpd.by else (None, interval)

                # If the bin has more than one value then the frequency has to be guessed
                if on_interval.left != on_interval.right:
                    condition = conditions.get(cpd.on, operator.Identity())
                    bin_freq = cpd.sub_bin_freqs[by_interval] if cpd.by else cpd.bin_freq
                    p = condition.calc_coverage(on_interval, p) * bin_freq

                by_overlap = tools.calc_interval_overlap(parent_interval, by_interval) if by_interval else 1

                # The node is a leaf
                if sub_tree.out_degree(cpd.on) == 0:
                    proba += p * by_overlap
                # The node is internal and we have to sum over it's children
                else:
                    for child in sub_tree.successors(cpd.on):
                        child_proba = propagate(child, on_interval)
                        proba += p * child_proba * by_overlap

            return proba

        sel = propagate(root)
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
