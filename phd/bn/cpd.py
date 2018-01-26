import pandas as pd


class CPD(pd.DataFrame):

    def __init__(self, df, on, by, relative=True):

        # Make sure by is a list
        by = by if isinstance(by, list) else [by]

        counts = df.groupby([on] + by).size().to_frame('count').reset_index()
        cpd = pd.pivot_table(data=counts, index=by, columns=on, values='count').fillna(0)

        if relative:
            cpd = cpd.div(cpd.sum(axis='columns'), axis='rows')

        super().__init__(data=cdp)

    @property
    def _constructor(self):
        return CPD
