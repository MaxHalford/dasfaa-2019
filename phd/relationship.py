class Relationship():

    def __init__(self, left, right, left_on, right_on):
        self.left = left
        self.right = right
        self.left_on = left_on
        self.right_on = right_on

    def __str__(self):
        return f'{self.left}.{self.left_on} <-> {self.right}.{self.right_on}'
