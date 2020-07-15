from typing import Hashable

from records import RecordBase


class Point(RecordBase):
    x: float
    y: float
    z: float = 0


p = Point(x=1.0, y=3.2)

assert p.x == 1.0
assert p.y == 3.2
assert p.z == 0
assert isinstance(p.z, int)
assert not isinstance(p, Hashable)

print(p)