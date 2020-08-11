from __future__ import annotations

from typing import Optional

from pytest import fixture, raises

from records import RecordBase, Annotated, check


@fixture(params=[True, False], ids=['frozen', 'mutable'])
def Point(request):
    class Point(RecordBase, frozen=request.param):
        x: float
        y: float
        z: float = 0

    Point.__qualname__ = 'Point'

    return Point


def test_unary(Point):
    assert Point({'x': 1, 'y': 2}) == Point(x=1, y=2)
    assert Point('{"x": 1, "y": 2}') == Point(x=1, y=2)
    assert Point(Point(x=1, y=2)) == Point(x=1, y=2)
    if Point.is_frozen():
        p = Point(x=1, y=2)
        assert Point(p) is p
    with raises(TypeError):
        Point((1, 2))


def test_unary_trivial_invalid():
    class Node(RecordBase, unary_parse=True):
        n: Optional[Node]

    assert Node(n=None) == Node(None)
    with raises(TypeError):
        Node({'n': 1})

    assert Node.parse({'n': 1}) == Node(1)


@fixture(params=[True, False], ids=['frozen', 'mutable'])
def Node(request):
    class Ret(RecordBase, frozen=request.param, unary_parse=True):
        n: Annotated[Optional[Ret], check]

        def __len__(self):
            if self.n is None:
                return 1
            return 1 + len(self.n)

    Ret.__qualname__ = 'Node'

    return Ret


def test_unary_trivial(Node):
    assert Node(None) == Node(n=None)
    assert Node({'n': None}) == Node(None)
    assert Node('{"n": null}') == Node(None)
    with raises(TypeError):
        Node(Node(None))


@fixture(params=[True, False], ids=['frozen', 'mutable'])
def Node_no_up(request):
    class Ret(RecordBase, frozen=request.param):
        n: Annotated[Optional[Ret], check]

        def __len__(self):
            if self.n is None:
                return 1
            return 1 + len(self.n)

    Ret.__qualname__ = 'Node'

    return Ret


def test_unary_trivial_noparse(Node_no_up):
    assert Node_no_up(None) == Node_no_up(n=None)
    assert Node_no_up(Node_no_up(None)) == Node_no_up(n=Node_no_up(n=None))


def test_unary_multiple(Point):
    class PointMixin:
        def __init__(self):
            super().__init__()
            self.x = 0
            self.y = 0

    class MapMixin(dict):
        def __init__(self):
            super().__init__(x=0, y=0)

    assert Point(PointMixin()) == Point(x=0, y=0)
    assert Point(MapMixin()) == Point(x=0, y=0)

    class mm(PointMixin, MapMixin):
        pass

    with raises(TypeError):
        Point(mm())
