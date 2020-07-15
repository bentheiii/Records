from pytest import fixture

from records import RecordBase


@fixture
def Point():
    class Point(RecordBase):
        x: float
        y: float
        z: float = 0

    return Point


def test_creation(Point):
    p = Point(x=3, y=2.5, z='zap')

    assert p.x == 3
    assert p.y == 2.5
    assert p.z == 'zap'


def test_default(Point):
    p = Point(x=3, y=2.5)

    assert p.x == 3
    assert p.y == 2.5
    assert p.z == 0
    assert isinstance(p.z, int)
