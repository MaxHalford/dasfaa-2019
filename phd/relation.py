import pandas as pd


class Relation(pd.DataFrame):

    def __init__(self, *args, **kwargs):
        name = kwargs.pop('name', None)
        super().__init__(*args, **kwargs)
        self.name = name

    @property
    def _constructor(self):
        return pd.DataFrame

    @property
    def attributes(self):
        return self.columns.tolist()
