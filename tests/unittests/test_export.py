from __future__ import annotations

from io import BytesIO, StringIO
from types import SimpleNamespace

from pytest import fixture, mark

from records import Annotated, RecordBase, Tag, check


@fixture(params=[True, False], ids=['frozen', 'mutable'])
def Point(request):
    class Point(RecordBase, frozen=request.param):
        x: float
        y: float
        z: float = 0

    Point.__qualname__ = 'Point'

    return Point


def test_export_dict(Point):
    p = Point(x=3, y=1, z=0)
    assert p.to_dict() == {'x': 3, 'y': 1}
    assert p.to_dict(include_defaults=True) \
           == p.to_dict.export_with(include_defaults=True)() \
           == {'x': 3, 'y': 1, 'z': 0}
    assert tuple(p.to_dict.export_with(sort=True)().values()) == (3, 1)
    assert tuple(p.to_dict
                 .export_with(include_defaults=True, sort=-1)()
                 .values()) \
           == (0, 1, 3)
    assert tuple(p.to_dict
                 .export_with(include_defaults=True, sort=lambda c: (ord(c) ** 2) % 7)()
                 .values()) \
           == (3, 0, 1)
    assert p.to_dict.select(keys_to_remove='x')(include_defaults=True) \
           == {'y': 1, 'z': 0}


def test_export_json(Point):
    p = Point(x=3, y=1, z=0)
    assert p.to_json() == '{"x": 3, "y": 1}'
    assert p.to_json.export_with(include_defaults=True)() \
           == '{"x": 3, "y": 1, "z": 0}'
    assert p.to_json.select(keys_to_remove='x').export_with(include_defaults=True)() \
           == '{"y": 1, "z": 0}'
    io = StringIO()
    p.to_json \
        .select(keys_to_remove='x') \
        .export_with(include_defaults=True)(io=io)
    assert io.getvalue() == '{"y": 1, "z": 0}'
    io.seek(0)
    assert Point.from_json_io.select(keys_to_add={'x': 1})(io) == Point(x=1, y=1)


class Point_g(RecordBase):
    x: float
    y: float
    z: float = 0


def test_pickle():
    p = Point_g(x=3, y=1, z=0)
    assert Point_g(p.to_pickle()) == p

    io = BytesIO()
    p.to_pickle(io=io)
    io.seek(0)
    assert Point_g.from_pickle_io(io) == p


def test_unpickle_parse(Point):
    p0 = Point_g(x=3, y=1, z=0)
    pickle = p0.to_pickle()
    assert Point.from_pickle(pickle) == Point(x=3, y=1)

    io = BytesIO()
    p0.to_pickle(io=io)
    io.seek(0)
    assert Point.from_pickle_io(io) == Point(x=3, y=1)


secret = Tag('secret')


@mark.parametrize('frozen', [True, False])
def test_blacklist(frozen):
    class User(RecordBase, frozen=frozen):
        user_name: Annotated[str, check]
        password: Annotated[str, check, secret]

    u = User(user_name="guest", password="swordfish")
    assert u.to_dict() == {"user_name": "guest", "password": "swordfish"}
    assert u.to_dict(blacklist_tags=secret) == {"user_name": "guest"}


a = Tag('a')
b = Tag('b')


@mark.parametrize('frozen', [True, False])
def test_whitelist(frozen):
    class Point(RecordBase, frozen=frozen):
        x: Annotated[int, check, a]
        y: Annotated[int, check, b]
        z: Annotated[int, check, a] = 0
        w: Annotated[int, check, b] = 0

    u = Point(x=3, y=2)
    assert u.to_dict() == {"x": 3, "y": 2}
    assert u.to_dict(blacklist_tags=Tag('b')) == {"x": 3}
    assert u.to_dict(whitelist_keys='w') == {"x": 3, "y": 2, "w": 0}
    assert u.to_dict(whitelist_keys=('w', 'y')) == {"x": 3, "y": 2, "w": 0}
    assert u.to_dict(blacklist_tags=Tag('b'), whitelist_keys='w') == {"x": 3, "w": 0}


def test_export_dict_foreign(Point):
    p = SimpleNamespace(x=3, y=1)
    assert Point.to_dict(p) == {'x': 3, 'y': 1}
    assert Point.to_dict(p, include_defaults=True) \
           == Point.to_dict.export_with(include_defaults=True)(p) \
           == {'x': 3, 'y': 1, 'z': 0}
    assert tuple(Point.to_dict.export_with(sort=True)(p).values()) == (3, 1)
    assert tuple(Point.to_dict
                 .export_with(include_defaults=True, sort=-1)(p)
                 .values()) \
           == (0, 1, 3)
    assert tuple(Point.to_dict
                 .export_with(include_defaults=True, sort=lambda c: (ord(c) ** 2) % 7)(p)
                 .values()) \
           == (3, 0, 1)
    assert Point.to_dict.select(keys_to_remove='x')(p, include_defaults=True) \
           == {'y': 1, 'z': 0}
