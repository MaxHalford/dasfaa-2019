import math
import random

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


def to_numeric(x):
    _, num = np.unique(x, return_inverse=True)
    return num

def calc_mutual_info(x: pd.Series, y: pd.Series):
    """Calculates the mutual information between two series.

    This works regarless of the type of each series.
    """

    # Determine the number of bins
    if bins == 'sqrt':
        bins = math.ceil(math.log(len(x)))

    # Convert the arrays to if they are not numeric
    null_fill = random.random()
    x = to_numeric(x.fillna(null_fill))
    y = to_numeric(x.fillna(null_fill))

    return metrics.mutual_info_score(x, y)
