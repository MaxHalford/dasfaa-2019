import pandas as pd


class CPD(pd.Series):

    def __init__(self, df, on, by):

        # Make sure by is a list
        by = [] if by is None else by
        by = [by] if not isinstance(by, list) else by

        if by:
            counts = df.groupby(by).apply(lambda g: g.groupby(on).size() / len(g))
        else:
            counts = df.groupby(on).size() / len(df)

        super().__init__(data=counts)

        self.on = on
        self.by = by

    @property
    def _constructor(self):
        return pd.Series
