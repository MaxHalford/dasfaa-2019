import itertools
from typing import List

import networkx as nx
import pandas as pd

from . import bayes_net
from . import dependence


def chow_liu_tree_from_df(df: pd.DataFrame, blacklist: List[str]) -> bayes_net.BayesNet:

    # Ignore columns that are part of the blacklist
    attributes = set(df.columns) - set(blacklist)
    if len(attributes) == 1:
        return bayes_net.BayesNet(nodes=attributes)

    # Calculate the pairwise mutual informations scores
    mut_infos = [
        (a, b, dependence.mutual_info(df[a], df[b]))
        for (a, b) in itertools.combinations(attributes, 2)
    ]

    # Create a graph that contains all the mutual informations
    mut_info_graph = nx.Graph()
    mut_info_graph.add_weighted_edges_from(mut_infos)

    # Determine the maximum spanning tree
    edges = nx.algorithms.tree.mst.maximum_spanning_edges(mut_info_graph)
    tree = nx.Graph()
    tree.add_edges_from(edges)
    tree = nx.bfs_tree(tree, list(tree.nodes)[0])

    # Initialise the Bayesian network
    bn = bayes_net.BayesNet(edges=list(tree.edges))

    return bn
