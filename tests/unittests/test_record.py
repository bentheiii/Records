from math import isclose
from types import SimpleNamespace
from typing import ClassVar, Dict, Hashable, List, Set

from pytest import fixture, mark, raises, skip

from records import Annotated, Factory, RecordBase, Tag, check
from records.select import Select

try:
    from typing import Final
except ImportError:
    Final = None


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
    assert p.to_dict() == {'x': 3.0, 'y': 2}
    assert p.to_dict.export_with(include_defaults=True)() == {'x': 3.0, 'y': 2, 'z': 0}


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


def test_removed_attr():
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
        addends: List[int] = Factory([].copy)

    assert Aggregator(3).addends is not Aggregator(3).addends


@mark.parametrize('frozen', [True, False])
def test_autofactory_copy(frozen):
    class Aggregator(RecordBase, frozen=frozen):
        start: int
        addends: Set[int] = Factory({1, 2, 3, 4}.copy)

    assert Aggregator(3).addends is not Aggregator(3).addends
    assert Aggregator(3).addends == {1, 2, 3, 4}


@mark.parametrize('frozen', [True, False])
def test_autofactory_underride(frozen):
    n = {"one": 1}

    class Aggregator(RecordBase, frozen=frozen):
        start: int
        addends: Dict[str, int] = n

    assert Aggregator(3).addends is Aggregator(3).addends is n


skip_without_final = mark.skipif(not Final, reason='Final not defined in standard library')


@skip_without_final
@mark.parametrize('frozen', [True, False])
def test_bad_record(frozen):
    with raises(TypeError):
        class _(RecordBase, frozen=frozen):
            # noinspection PyFinal
            x: Final


@skip_without_final
def test_bad_record_frozen_spec():
    with raises(TypeError):
        class _(RecordBase):
            # noinspection PyFinal
            x: Final[int]


@skip_without_final
def test_record_frozen_spec():
    class A(RecordBase, frozen=True):
        # noinspection PyFinal
        x: Final[int]

    a = A(3)
    assert a.x == 3


def test_from_mapping(Point):
    d = {'x': 3, 'y': 2.0}
    assert Point.from_mapping(d) == Point(x=3, y=2.0)
    d = {'x_': 3, 'y': 2.0, 'g': 'howdy'}
    assert Point.from_mapping.select(keys_to_remove='g', keys_to_rename=[('x_', 'x')])(d) \
           == Point(x=3, y=2.0)
    assert Point.from_mapping.select(
        keys_to_remove='g',
        keys_to_rename=[('x_', 'x')],
        keys_to_maybe_rename=[('Y', 'y')]
    )(d) == Point(x=3, y=2.0)
    assert Point.from_mapping.select(
        keys_to_remove='g',
        keys_to_rename={'x_': 'x'},
        keys_to_maybe_rename={'Y': 'y'}
    )(d) == Point(x=3, y=2.0)
    assert Point.from_mapping.select(
        keys_to_remove='g',
        keys_to_rename={'x_': 'x'},
        keys_to_maybe_rename={'Y': 'y'},
        keys_to_add={'z': 3}
    )(d) == Point(x=3, y=2.0, z=3)
    assert Point.from_mapping.select(
        keys_to_remove='g',
        keys_to_maybe_rename={'Y': 'y', 'x_': 'x'},
        keys_to_add={'z': 3}
    )(d) == Point(x=3, y=2.0, z=3)
    assert Point.from_mapping.select(
        keys_to_remove='g',
        keys_to_maybe_rename={'Y': 'y', 'x_': 'x'},
        keys_to_maybe_add={'z': 3}
    )(d) == Point(x=3, y=2.0, z=3)
    with raises(TypeError):
        Point.from_mapping(d)
    d = {'x': 3, 'y': 2.0, 'g': 'howdy', 'z': 2}
    assert Point.from_mapping.select(
        Select(keys_to_remove='g', keys_to_maybe_remove='j'),
        Select.empty,  # cover merging with empty
        keys_to_maybe_add={'z': 3}
    )(d) == Point(x=3, y=2.0, z=2)
    with raises(ValueError):
        assert Point.from_mapping.select(
            keys_to_remove='g',
            keys_to_add={'z': 3}
        )(d)
    with raises(ValueError):
        assert Point.from_mapping.select(
            keys_to_rename={'x': 'z'}
        )(d)
    with raises(ValueError):
        assert Point.from_mapping.select(
            keys_to_maybe_rename={'x': 'z'}
        )(d)


def test_from_instance(Point):
    p = Point(x=1, y=2, z=3)
    assert Point.from_instance(p) == p
    if Point.is_frozen():
        assert Point.from_instance(p) is p
        assert Point.from_instance(p, z=4) is not p
        assert Point.from_instance(p, {}) is not p
    else:
        assert Point.from_instance(p) is not p
    assert Point.from_instance(p, z=4) == Point(x=1, y=2, z=4)
    assert Point.from_instance.select(keys_to_remove='z')(p) == Point(x=1, y=2)
    mp = SimpleNamespace(x=1, y=2, z=3)
    assert Point.from_instance(mp) == p


def test_from_json(Point):
    p = Point(x=1, y=2, z=3)
    s = '{"x":1,"y":2,"z":3}'
    assert Point.from_json(s) == p
    assert Point.from_json.select(keys_to_remove='z')(s) == Point(x=1, y=2)


def test_bad_cmp(Point):
    p1 = Point(x=1, y=2)
    p2 = Point(x=2, y=1)
    with raises(TypeError):
        assert p1 >= p2


def test_dumb_hint():
    class A(RecordBase):
        x: 12

    assert A(3).x == 3


def test_circular():
    class A(RecordBase):
        x: 'A'

    assert A(A(None)).x.x is None


def test_classvar():
    class A(RecordBase):
        x: 'A'
        y: ClassVar[int]

    assert A(A(None)).x.x is None
    assert 'y' not in A._fields


def test_nofield():
    with raises(ValueError):
        class A(RecordBase):
            pass


def test_get_by_tag():
    class A(RecordBase):
        a0: Annotated[int, Tag(0)]
        b1: Annotated[int, Tag(1)]
        c0: Annotated[int, Tag(0)]

    assert A._fields.filter_by_tag(Tag(0)) == {'a0': A.a0, 'c0': A.c0}


def test_exception_has_field_name():
    class A(RecordBase, default_type_check=check):
        field_one: int
        field_two: str

    with raises(TypeError, match='field_two'):
        A(field_one=12, field_two=11)
