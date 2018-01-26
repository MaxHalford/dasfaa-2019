from . import dag
from . import dependence


def build_chow_liu_tree_from_table(df):

    # Calculate the pairwise mutual informations scores
    mut_infos = []
    for i, col_x in enumerate(df.columns):
        for col_y in df.columns[i:]:
            print(col_x, col_y)

    # Initialise the list of dependencies
    dependencies = []

    # Initalise a DAG with the obtained dependencies
    tree = dag.DAG(dependencies=dependencies)

    return tree
