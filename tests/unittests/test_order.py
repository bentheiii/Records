from pytest import fixture, raises

from records import RecordBase, Annotated, exclude_from_ordering


@fixture(params=[True, False], ids=['frozen', 'mutable'])
def Point(request):
    class Point(RecordBase, frozen=request.param, ordered=True):
        x: float
        y: float
        text: Annotated[str, exclude_from_ordering]

    Point.__qualname__ = 'Point'

    return Point


def test_ordering(Point):
    p1 = Point(x=1, y=-60, text='a')
    p2 = Point(x=2, y=30, text='')
    assert p1 < p2
    assert p1 <= p2
    assert p2 > p1
    assert p2 >= p1


def test_excluded(Point):
    p1 = Point(x=1, y=30, text='a')
    p2 = Point(x=1, y=30, text='b')
    assert not p1 < p2
    assert p1 <= p2
    assert p2 <= p1
    assert not p2 > p1
    assert p2 >= p1
    assert p1 >= p2
    assert p2 != p1


def test_pad_order(Point):
    p1 = Point(x=1, y=-60, text='a')
    with raises(TypeError):
        assert p1 >= 0
    with raises(TypeError):
        assert p1 <= 0
    with raises(TypeError):
        assert p1 > 0
    with raises(TypeError):
        assert p1 < 0
