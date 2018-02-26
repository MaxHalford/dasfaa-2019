from typing import Iterable

import pandas as pd

from phd import tools


class Operator():

    def __init__(self, operand):
        self.operand = operand

    def calc_coverage(self, interval: pd.Interval, n_values=1):
        raise NotImplementedError


class Identity(Operator):

    def __init__(self):
        pass

    def calc_coverage(self, interval: pd.Interval, n_values: int):
        return 1


class Equal(Operator):

    def calc_coverage(self, interval: pd.Interval, n_values: int):

        if isinstance(self.operand, pd.Interval):
            return tools.calc_interval_overlap(interval, self.operand)

        return 1 / n_values if self.operand in interval else 0


class Less(Operator):

    def calc_coverage(self, interval: pd.Interval, n_values: int):
        if interval.left == interval.right:
            return 1 if interval.right < self.operand else 0
        if self.operand in interval:
            return (self.operand - interval.left) / (interval.right - interval.left)
        return 1 if interval.right < self.operand else 0


class In(Operator):

    def __init__(self, iterable: Iterable):
        self.iterable = iterable

    def calc_coverage(self, interval: pd.Interval, n_values: int):
        for i in self.iterable:
            if Equal(i).calc_coverage(interval, 1) > 0:
                return 1
        return 0
