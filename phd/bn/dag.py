import networkx as nx


class DAG(nx.DiGraph):

    def __init__(self, dependencies):
        """

        Args:
            dependencies (list of tuples): list of two-valued tuples indicating
                the directed dependencies between the nodes. The nodes are
                guessed from the list of dependencies.
        """

        super().__init__()

        # Add the nodes
        self.add_nodes_from(set(itertools.chain(*dependencies)))

        # Add the dependencies
        self.add_edges_from(dependencies)

    @property
    def is_acyclic(self):
        """Checks if the DAG is acyclic or not."""
        return next(nx.simple_cycles(dag), None) is None

    def draw(self, ax):
        """Draws the DAG on a matplotlib.axis."""
        nx.draw(
            dag,
            with_labels=True,
            ax=ax,
            **{
                'node_color': 'black',
                'node_size': 1000,
                'width': 2,
            }
        )
