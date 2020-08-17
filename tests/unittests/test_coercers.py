from collections import defaultdict, deque, namedtuple
from enum import Enum
from fractions import Fraction
from re import Pattern, compile
from typing import DefaultDict, Deque, Iterable, Mapping, Sequence, Tuple, Union

from pytest import mark, raises

from records import (Annotated, CallCoercion, ClassMethodCoercion, ComposeCoercer, Encoding, Eval, FromInteger, Loose,
                     LooseUnpack, LooseUnpackMap, MapCoercion, RecordBase, SingletonFromFalsish, TypeCheckStyle, Whole,
                     check, check_strict)
from records.fillers.builtin_fillers.std_fillers import ToBytes


def ACls(T, *args):
    annotated = Annotated.__class_getitem__((T, TypeCheckStyle.check, *args))

    class A(RecordBase):
        x: annotated

    def ret(v, ex=None):
        a = A(v)
        assert isinstance(a.x, type(ex))
        assert a.x == ex

    return ret


def test_float():
    a = ACls(float, Loose, Eval(float))
    a(2.0, 2.0)
    a(6, 6.0)
    a(True, 1.0)
    a('2.0', 2.0)
    a('float(6+9)', 15.0)
    with raises(TypeError):
        a(())
    with raises(TypeError):
        a('95/0.0')
    with raises(TypeError):
        a('95 + 0')


def test_float_loose():
    a = ACls(float, Loose, ComposeCoercer(Loose, Eval(float)))
    a(2.0, 2.0)
    a(6, 6.0)
    a(True, 1.0)
    a('2.0', 2.0)
    a('6+9', 15.0)
    with raises(TypeError):
        a(())
    with raises(TypeError):
        a('95/0.0')


def test_bad_loose():
    with raises(TypeError):
        ACls(Iterable, Loose)


def test_loose_unpack():
    a = ACls(range, LooseUnpack)
    a(range(1, 10, 2), range(1, 10, 2))
    a((1, 10, 2), range(1, 10, 2))
    a((1, 10), range(1, 10))
    a((10,), range(10))
    with raises(TypeError):
        a(10)


def test_loose_unpack_map():
    t = namedtuple('t', 'a b c', defaults=(0,))
    a = ACls(t, LooseUnpackMap)
    a(t(1, 10, 2), t(1, 10, 2))
    a({'a': 1, 'b': 10, 'c': 2}, t(1, 10, 2))
    a({'a': 1, 'b': 10}, t(1, 10))
    with raises(TypeError):
        a(10)


def test_whole():
    a = ACls(int, TypeCheckStyle.check_strict, Whole)
    a(3, 3)
    a(True, 1)
    a(3.0, 3)
    a(Fraction(4, 2), 2)
    a(1.0 + 0j, 1)
    with raises(TypeError):
        a(2.5)
    with raises(TypeError):
        a(Fraction(4, 3))
    with raises(TypeError):
        a("15")
    with raises(TypeError):
        a(1 + 1j)


def test_from_bytes():
    a = ACls(int, ClassMethodCoercion('from_bytes', byteorder='big'))
    a(6, 6)
    a(True, True)
    a(b'', 0)
    a(b'\x01\x33', 256 + 3 * 16 + 3)
    a([], 0)
    a([2, 18], 2 * 256 + 18)
    with raises(ValueError):
        a([300])


def test_to_bytes():
    a = ACls(bytearray, ToBytes(byteorder='big'))
    a(bytearray(b'23'), bytearray(b'23'))
    a(12, bytearray([12]))
    a(300, bytearray([1, 300 - 256]))
    with raises(TypeError):
        a(25.6)


def test_to_bytes_setlength():
    a = ACls(bytearray, ToBytes(1, byteorder='big'))
    a(bytearray(b'23'), bytearray(b'23'))
    a(12, bytearray([12]))
    with raises(TypeError):
        a(25.6)
    with raises(OverflowError):
        a(300)


def test_from_int():
    a = ACls(bool, FromInteger)
    a(True, True)
    a(0, False)
    a(1, True)
    a(1.0, True)
    with raises(TypeError):
        a(2)


@mark.parametrize('t,i', [(None, None), (type(None), None), (type(...), ...)])
def test_singleton(t, i):
    a = ACls(t, SingletonFromFalsish)
    a(i, i)
    a(False, i)
    a([], i)
    a('', i)
    with raises(TypeError):
        a('nill')


def test_encoding():
    a = ACls(str, Encoding('ascii'))
    a('abc', 'abc')
    a(b'abc', 'abc')
    with raises(ValueError):
        a(b'abc\xff')


def test_many_union():
    a = ACls(Union[Annotated[bool, TypeCheckStyle.check_strict, FromInteger], Annotated[float, Loose]])
    a('3.6', 3.6)
    a(True, True)
    a(1.0, 1.0)
    with raises(ValueError):
        a(1)


def test_func_coerce():
    a = ACls(Pattern, CallCoercion(compile))
    a('.*', compile('.*'))


def test_func_map():
    d = {
        'true': True,
        'false': False,
        'yes': True,
        'no': False,
        'y': True,
        'n': False
    }
    a = ACls(bool, ComposeCoercer(MapCoercion(d), CallCoercion(str.lower)))
    a(True, True)
    a(False, False)
    a('Y', True)
    a('false', False)
    with raises(TypeError):
        a('maybe')


def test_func_map_fact():
    class C:
        i = 0

        def __init__(self):
            type(self).i += 1

        def __eq__(self, other):
            return type(self) == type(other)

    d = {
        'c': C,
    }
    a = ACls(C, MapCoercion(factory_map=d))
    s = C()
    a('c', s)
    a('c', s)
    assert C.i == 3
    with raises(TypeError):
        a('lu')


def test_inner_coercer():
    a = ACls(Sequence[Annotated[int, TypeCheckStyle.check, Loose]], TypeCheckStyle.check)
    a([], [])
    a([1, 2], [1, 2])
    a([1.2, 1, 3], [1, 1, 3])
    a([1, 3, 1.2], [1, 3, 1])
    a((1, 1.2, 1), (1, 1, 1))


def test_inner_coercer_tuple_ell():
    a = ACls(Tuple[Annotated[int, TypeCheckStyle.check, Loose], ...], TypeCheckStyle.check)
    a((), ())
    a((1, 2), (1, 2))
    a((1.2, 1, 3), (1, 1, 3))
    a((1, 3, 1.2), (1, 3, 1))
    a((1, 1.2, 1), (1, 1, 1))
    a((1, 1.2, 1.2), (1, 1, 1))


def test_inner_coercer_tuple():
    a = ACls(Tuple[
                 Annotated[int, TypeCheckStyle.check, Loose],
                 Annotated[float, TypeCheckStyle.check, Eval],
                 Annotated[str, TypeCheckStyle.check, CallCoercion(repr)],
             ], TypeCheckStyle.check)
    a((1, 3.2, 'a'), (1, 3.2, 'a'))
    a((5.3, 5.2, '5.2'), (5, 5.2, '5.2'))
    a((6, '6.0+9.1', 'hi'), (6, 15.1, 'hi'))
    a((6, '6.0+9.1', True), (6, 15.1, 'True'))


def test_inner_coercer_deque():
    a = ACls(Deque[Annotated[int, TypeCheckStyle.check, Loose]], TypeCheckStyle.check)
    a(deque(), deque())
    a(deque([1, 2]), deque([1, 2]))
    a(deque([1.2, 1, 3]), deque([1, 1, 3]))
    a(deque([1, 3, 1.2]), deque([1, 3, 1]))
    a(deque((1, 1.2, 1)), deque((1, 1, 1)))


def test_inner_coercer_map():
    a = ACls(Mapping[int, Annotated[float, TypeCheckStyle.check, Loose]], TypeCheckStyle.check)
    a({}, {})
    a({9: 3}, {9: 3.0})
    a({64: 8.0, 9: 3}, {9: 3.0, 64: 8.0})
    a({64: 8, 9: 3}, {9: 3.0, 64: 8.0})


def test_inner_coercer_defaultmap():
    a = ACls(DefaultDict[int, Annotated[float, TypeCheckStyle.check, Loose]], TypeCheckStyle.check)
    a(defaultdict(lambda: -1.0, {}), defaultdict(lambda: -1.0, {}))
    a(defaultdict(lambda: -1.0, {9: 3}), defaultdict(lambda: -1.0, {9: 3.0}))
    a(defaultdict(lambda: -1.0, {64: 8.0, 9: 3}), defaultdict(lambda: -1.0, {9: 3.0, 64: 8.0}))
    a(defaultdict(lambda: -1.0, {64: 8, 9: 3}), defaultdict(lambda: -1.0, {9: 3.0, 64: 8.0}))


def test_bad_type():
    with raises(ValueError):
        class _(RecordBase):
            x: Annotated[int, Loose]


def test_union_join():
    a = ACls(Union[bool, float], Eval)
    a('3.6', 3.6)
    a(True, True)
    a(1.0, 1.0)
    a("True", True)
    with raises(TypeError):
        a("1")
    with raises(TypeError):
        a(1)


def test_union_unequal():
    class A(RecordBase):
        x: Union[Annotated[int, check_strict, Eval], Annotated[str, check]]

    assert A(x=5).x == 5
    assert A(x="a").x == "a"
    assert A(x="12").x == "12"

    class A(RecordBase):
        x: Union[Annotated[int, check_strict, Loose], Annotated[Pattern, check, CallCoercion(compile)]]

    assert A(x=5).x == 5
    assert A(x="a").x == compile("a")
    with raises(ValueError):
        A(x="12")


def test_eval_enum():
    class E(Enum):
        x = 1
        y = 2
        z = 3

    a = ACls(E, Eval(E))
    a('E(1)', E(1))
    a('E.x', E.x)
    with raises(TypeError):
        a('1')


def test_eval_ellipsis():
    class E(Enum):
        x = 1
        y = 2
        z = 3

    a = ACls(E, Eval(...))
    a('E(1)', E(1))
    a('E.x', E.x)
    with raises(TypeError):
        a('1')
