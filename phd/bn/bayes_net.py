import itertools
import numbers
import re

import networkx as nx
import pandas as pd

from phd import operator
from phd import tools

from . import distribution


def discretize_series(series: pd.Series, n_mcv: int, n_bins: int) -> pd.Series:

    s = series.copy()

    # Remove trailing whitespace
    if s.dtype == 'object':
        s = s.str.rstrip()

    # Treat most common values
    value_counts = s.value_counts()
    n_mcv = len(value_counts) if n_mcv == -1 else n_mcv
    n_largest = value_counts.nlargest(n_mcv)
    most_common_vals = set(n_largest.index)
    most_common_mask = s.isin(most_common_vals)

    # Treat least common values
    n_least_common = s[~most_common_mask].nunique()
    n_bins = min(n_least_common, n_bins)
    if n_least_common > 0:
        # Histogram for categorical data
        if not isinstance(s.iloc[0], numbers.Number):
            s[~most_common_mask] = tools.categorical_qcut(s[~most_common_mask], q=n_bins)
        # Histogram for continuous data
        else:
            s[~most_common_mask] = pd.qcut(s[~most_common_mask], q=n_bins, duplicates='drop')

    # Replace np.nan with None
    s = s.where((pd.notnull(s)), None)

    # Count the number of distinct values per bin
    n_distinct = {}
    for hist_bin in s[~most_common_mask].unique():
        if hist_bin is not None:
            n_distinct[str(hist_bin)] = len(set(x for x in series if x and x in hist_bin))

    # Convert everything to strings
    def format(x):
        if isinstance(x, pd.Interval):
            return '[{} %,% {}]'.format(x.left, x.right)
        return str(x)
    s = s.apply(format)

    return s, n_distinct


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

    def update_distributions(self, df: pd.DataFrame, n_mcv: int, n_bins: int, types: dict):
        """Updates each node's CDP given the data in a pandas.DataFrame."""

        # Copy the DataFrame before applying discretization; this wastes RAM
        df = df[list(self.nodes)].copy()

        # Record the number of distinct values per histogram
        self.n_distinct = {}

        # Dicretization
        for col in df.columns:
            df[col], self.n_distinct[col] = discretize_series(df[col], n_mcv=n_mcv, n_bins=n_bins)

        # Compute each attribute's distribution
        for node in self.nodes:
            predecessor = next(self.predecessors(node), None)
            self.node[node]['dist'] = distribution.Distribution(on=node, by=predecessor)
            self.node[node]['dist'].from_df(df, types=types)

    def infer(self, conditions) -> float:

        sub_tree = self.steiner_tree(conditions.keys())

        root = sub_tree.root()

        def subset_dist(on):

            by = sub_tree.node[on]['dist'].by

            sub_tree.node[on]['dist'] = sub_tree.node[on]['dist'].subset(on, conditions.get(on))
            if by:
                sub_tree.node[on]['dist'] = sub_tree.node[on]['dist'].subset(by, conditions.get(by))

            child_conditions = [subset_dist(child) for child in sub_tree.successors(on)]
            for condition in child_conditions:
                sub_tree.node[on]['dist'] = sub_tree.node[on]['dist'].subset(on, condition)

            if by:
                return operator.In(set(sub_tree.node[on]['dist'].keys()))

        def propagate(node):

            # Get the node's CPD
            dist = sub_tree.node[node]['dist']

            # We're at a leaf of the tree
            if sub_tree.out_degree(node) == 0:
                return {
                    by_val: sum(
                        (p * conditions[node].calc_coverage(on_val, self.n_distinct[node][str(on_val)]))
                        if isinstance(on_val, pd.Interval) and node in conditions
                        else p
                        for on_val, p in d.items()
                    )
                    for by_val, d in dist.items()
                }

            child_dists = [propagate(child) for child in sub_tree.successors(node)]

            # We're at an internal node
            if dist.by:
                return {
                    by_val: sum(
                        sum(
                            child_dist[on_val] *
                                (
                                    (p * conditions[node].calc_coverage(on_val, self.n_distinct[node][str(on_val)]))
                                    if isinstance(on_val, pd.Interval) and node in conditions
                                    else p
                                )
                            for on_val, p in d.items()
                        )
                        for child_dist in child_dists
                    )
                    for by_val, d in dist.items()
                }

            # We're at the root of the tree
            return sum(
                sum(
                    p * child_dist[on_val]
                    for child_dist in child_dists
                )
                for on_val, p in dist.items()
            )

        subset_dist(root)
        sel = propagate(root)
        return sel

    def infer2(self, conditions) -> float:

        sub_tree = self.steiner_tree(conditions.keys())

        root = sub_tree.root()

        def subset_dist(on):

            by = sub_tree.node[on]['dist'].by

            sub_tree.node[on]['dist'] = sub_tree.node[on]['dist'].subset(on, conditions.get(on))
            if by:
                sub_tree.node[on]['dist'] = sub_tree.node[on]['dist'].subset(by, conditions.get(by))

            child_conditions = [subset_dist(child) for child in sub_tree.successors(on)]
            for condition in child_conditions:
                sub_tree.node[on]['dist'] = sub_tree.node[on]['dist'].subset(on, condition)

            if by:
                return operator.In(set(sub_tree.node[on]['dist'].keys()))

        def propagate(node, by_val=None):

            # Get the node's CPD
            dist = sub_tree.node[node]['dist']

            # Filter the CPD based on the parent's value
            if by_val:
                dist = dist[by_val]
            proba = 0

            for val, p in dist.items():

                # If the bin has more than one value then the frequency has to be guessed
                if isinstance(val, pd.Interval) and node in conditions:
                    p *= conditions[node].calc_coverage(val, self.n_distinct[node][str(val)])

                # The node is a leaf
                if sub_tree.out_degree(node) == 0:
                    proba += p
                # The node is internal and we have to sum over it's children
                else:
                    for child in sub_tree.successors(node):
                        proba += p * propagate(child, val)

            return proba

        subset_dist(root)
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
