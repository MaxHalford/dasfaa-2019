from typing import Iterable

import pandas as pd

from phd import tools


class Operator():

    def __init__(self, operand):
        self.operand = operand

    def calc_coverage(self, interval: pd.Interval, n_values=1):
        raise NotImplementedError

    def keep_relevant(self, values):
        return NotImplementedError

    def __str__(self) -> str:
        raise NotImplementedError

    def __repr__(self) -> str:
        return str(self)


class Identity(Operator):

    def __init__(self):
        pass

    def calc_coverage(self, interval: pd.Interval, n_values: int):
        return 1

    def keep_relevant(self, values):
        return set(values)

    def __str__(self) -> str:
        return '1'


class Equal(Operator):

    def calc_coverage(self, interval: pd.Interval, n_values: int):

        if isinstance(self.operand, pd.Interval):
            return tools.calc_interval_overlap(interval, self.operand)

        return 1 / n_values if self.operand in interval else 0

    def keep_relevant(self, values):
        if self.operand in values:
            return set(v for v in values if v == self.operand)
        return set(v for v in values if v and self.operand in v)

    def __str__(self) -> str:
        return 'x == {}'.format(self.operand)


class In(Operator):

    def __init__(self, iterable: Iterable):
        self.iterable = iterable

    def calc_coverage(self, interval: pd.Interval, n_values: int):
        for i in self.iterable:
            if Equal(i).calc_coverage(interval, 1) > 0:
                return 1
        return 0

    def keep_relevant(self, values):
        return set(val for val in values if val in self.iterable)

    def __str__(self) -> str:
        return 'x in {}'.format(self.operand)
