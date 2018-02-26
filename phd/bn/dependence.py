import datetime as dt
import random
import time

import numpy as np
import pandas as pd
from sklearn import metrics


def to_numeric(x: pd.Series):
    _, num = np.unique(x.tolist(), return_inverse=True)
    return num


def mutual_info(x: pd.Series, y: pd.Series):
    """Calculates the mutual information between two series.

    This works regardless of the type of each series.
    """
    null_mask = x.isnull() | y.isnull()
    try:
        return metrics.mutual_info_score(to_numeric(x[~null_mask]), to_numeric(y[~null_mask]))
    except:
        return 0
