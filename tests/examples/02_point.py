from typing import Hashable

from records import RecordBase


class Point(RecordBase, frozen=True):
    x: float
    y: float
    z: float = 0


p = Point(x=1.0, y=3.2)
assert isinstance(p, Hashable)
