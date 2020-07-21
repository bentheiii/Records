from math import isclose
from typing import Hashable, List, Set, Dict

from pytest import fixture, mark, raises, skip

from records import Factory, RecordBase, DefaultValue


@fixture(params=[True, False], ids=['frozen', 'mutable'])
def Point(request):
    class Point(RecordBase, frozen=request.param):
        x: float
        y: float
        z: float = 0

    Point.__qualname__ = 'Point'

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


def test_required(Point):
    with raises(TypeError):
        Point(x=3, z=2)


def test_eq(Point):
    p1 = Point(x=3.0, y=2)
    p2 = Point(x=3, y=2, z=0)
    assert p1 == p2
    p3 = Point(x=3.0, y=2, z=1)
    assert p1 != p3 != p2
    assert p1 != {'x': 3.0, 'y': 2, 'z': 0}


def test_dict_eq(Point):
    p = Point(x=3.0, y=2)
    assert p.as_dict() == {'x': 3.0, 'y': 2, 'z': 0}


def test_repr(Point):
    p = Point(x=3, y=2.5)
    assert eval(repr(p)) == p


def test_mutable(Point):
    if True:
        skip()
    p1 = Point(x=3.0, y=2, z=1)
    p2 = Point(x=3, y=2, z=0)
    assert p1 != p2
    p2.z = 1
    assert p1 == p2
    with raises(TypeError):
        hash(p1)
    assert not issubclass(Point, Hashable)


def test_immutable(Point):
    if not Point.is_frozen():
        skip()
    p1 = Point(x=3.0, y=2, z=1)
    p2 = Point(x=3, y=2, z=0)
    with raises(TypeError):
        p2.z = 1
    hash(p1)
    assert issubclass(Point, Hashable)


def test_unslotted(Point):
    if Point.is_frozen():
        skip()
    p = Point(x=3, y=2.5)
    p.t = 't'
    assert p.t == 't'


def test_slotted(Point):
    if Point.is_frozen():
        skip()
    p = Point(x=3, y=2.5)
    p.t = 't'
    assert p.t == 't'


def test_ignored_attr():
    class IPoint(RecordBase):
        a = 1

        x: float
        y: float
        z: float = 0

        def norm(self):
            return self.norm_sq() ** 0.5

        def norm_sq(self) -> float:
            return self.x ** 2 + self.y ** 2 + self.z ** 2

    p = IPoint(x=3, y=4)

    assert isclose(p.norm(), 5)
    assert isclose(p.norm_sq(), 25)

    assert IPoint.a == 1
    assert p.a == 1


def test_bad_hint():
    with raises(TypeError):
        class IPoint(RecordBase):
            x: float
            y: float
            z: 2 = 0


def test_bad_arg(Point):
    with raises(TypeError):
        Point(x=1, y=2, a=3)

    with raises(TypeError):
        Point(1, 2)

    with raises(TypeError):
        Point(1, y=2)


@mark.parametrize('frozen', [True, False])
def test_factory(frozen):
    class Aggregator(RecordBase, frozen=frozen):
        start: int
        addends: List[int] = Factory(list)

    assert Aggregator(3).addends is not Aggregator(3).addends


@mark.parametrize('frozen', [True, False])
def test_autofactory(frozen):
    class Aggregator(RecordBase, frozen=frozen):
        start: int
        addends: List[int] = []

    assert Aggregator(3).addends is not Aggregator(3).addends


@mark.parametrize('frozen', [True, False])
def test_autofactory_copy(frozen):
    class Aggregator(RecordBase, frozen=frozen):
        start: int
        addends: Set[int] = {1, 2, 3, 4}

    assert Aggregator(3).addends is not Aggregator(3).addends
    assert Aggregator(3).addends == {1, 2, 3, 4}


@mark.parametrize('frozen', [True, False])
def test_autofactory_underride(frozen):
    n = {"one": 1}

    class Aggregator(RecordBase, frozen=frozen):
        start: int
        addends: Dict[str, int] = DefaultValue(n)

    assert Aggregator(3).addends is Aggregator(3).addends is n
