from typing import Hashable


class Tag:
    """
    A tag to mark a Field as belonging to a category. Tags encapsulate a single hashable object and implement only
     hashing and equality.
    """
    def __init__(self, x: Hashable):
        self.inner = x

    def __hash__(self):
        return hash(self.inner)

    def __eq__(self, other):
        return type(other) == type(self) \
               and self.inner == other.inner

    def __repr__(self):
        return f'Tag({self.inner!r})'
