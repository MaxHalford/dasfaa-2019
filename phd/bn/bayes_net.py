import networkx as nx
import pandas as pd

from phd import distribution
from phd import operator as op
from phd import tools


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
            return to_p(node, parent) + ''.join([
                concat(child, node)
                for child in self.successors(node)
            ])

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
        self.n_in_bin = {}

        # Dicretization
        for col in df.columns:
            df[col], self.n_in_bin[col] = tools.discretize_series(
                df[col],
                n_mcv=n_mcv,
                n_bins=n_bins
            )

        # Compute each attribute's distribution
        for node in self.nodes:
            predecessor = next(self.predecessors(node), None)
            self.node[node]['dist'] = distribution.Distribution(on=node, by=predecessor)
            self.node[node]['dist'].build_from_df(df, types=types)

    def infer(self, conditions) -> float:

        sub_tree = self.steiner_tree(conditions.keys())

        root = sub_tree.root()

        def subset_dist(on):

            by = sub_tree.node[on]['dist'].by

            child_conditions = [subset_dist(child) for child in sub_tree.successors(on)]
            for condition in child_conditions:
                sub_tree.node[on]['dist'] = sub_tree.node[on]['dist'].subset(on, condition)

            sub_tree.node[on]['dist'] = sub_tree.node[on]['dist'].subset(on, conditions.get(on))
            if by:
                sub_tree.node[on]['dist'] = sub_tree.node[on]['dist'].subset(by, conditions.get(by))

            if by:
                return op.In(set(sub_tree.node[on]['dist'].keys()))

        def propagate(node):

            # Get the node's CPD
            dist = sub_tree.node[node]['dist']

            # We're at a leaf of the tree
            if sub_tree.out_degree(node) == 0:

                if not dist.by:
                    return sum(dist.values())

                return {
                    by_val: sum(
                        (p * conditions[node].calc_coverage(on_val, self.n_in_bin[node][str(on_val)]))
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
                                (p * conditions[node].calc_coverage(on_val, self.n_in_bin[node][str(on_val)]))
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
