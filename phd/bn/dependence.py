import random

import numpy as np
import pandas as pd
from sklearn import metrics


def to_numeric(x):
    _, num = np.unique(x.tolist(), return_inverse=True)
    return num

def mutual_info(x: pd.Series, y: pd.Series):
    """Calculates the mutual information between two series.

    This works regardless of the type of each series.
    """

    # Convert the arrays to if they are not numeric
    null_fill = random.random()
    x = to_numeric(x.fillna(null_fill))
    y = to_numeric(y.fillna(null_fill))

    return metrics.mutual_info_score(x, y)
