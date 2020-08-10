from typing import Iterable, Any
from unittest.mock import Mock

from pytest import raises, mark, warns

from records import Annotated, Loose, RecordBase, TypeCheckStyle, Within, Clamp, Cyclic, \
    FullMatch, Truth, AssertCallValidation, CallValidation


def ACls(T, *args):
    class A(RecordBase):
        x: Annotated[T, TypeCheckStyle.check, args]

    def ret(v, ex=None):
        a = A(v)
        assert isinstance(a.x, type(ex))
        assert a.x == ex

    return ret


@mark.parametrize('T', [int, float])
def test_positive(T):
    a = ACls(T, Loose, Within(0))
    a(65.0, T(65))
    with raises(ValueError):
        a(-9.0)


@mark.parametrize('T', [int, float])
def test_lt_100(T):
    a = ACls(T, Loose, Within(lt=100, l_eq=True))
    a(65.0, T(65))
    a(100, T(100))
    with raises(ValueError):
        a(101)


@mark.parametrize('T', [int, float])
def test_between_10_100(T):
    a = ACls(T, Loose, Within(10, lt=100, g_eq=False))
    a(65.0, T(65))
    a(11, T(11))
    with raises(ValueError):
        a(10)
    with raises(ValueError):
        a(100)


def test_clamp():
    a = ACls(int, Clamp(10, 100))
    a(15, 15)
    a(101, 100)
    a(3, 10)


def test_Cyclic():
    a = ACls(int, Cyclic(10, 100))
    a(15, 15)
    a(101, 11)
    a(3, 93)


def test_equation():
    pattern = r'[0-9]+(\s*[-+*/]\s*[0-9]+)*'
    a = ACls(str, FullMatch(pattern, err=LookupError()))
    a('0+9+3+1', '0+9+3+1')
    a('95', '95')
    with raises(LookupError):
        a('a**3')


def test_notempty():
    a = ACls(Any, Truth)
    a('hi', 'hi')
    a(12, 12)
    with raises(ValueError):
        a([])


def test_warn():
    a = ACls(Any, Truth(warn=True))
    a('hi', 'hi')
    a(12, 12)
    with warns(UserWarning):
        a([], [])


def test_warn_logger():
    logger = Mock()
    a = ACls(Any, Truth(warn=logger))
    a('hi', 'hi')
    a(12, 12)
    a([], [])
    logger.warning.assert_called_once()


def test_assert_call():
    a = ACls(Iterable, AssertCallValidation(lambda v: len(v) >= 2))
    a('hi', 'hi')
    a(range(3), range(3))
    with raises(ValueError):
        a(range(0))
    with raises(TypeError):
        a(x for x in range(1000))


def test_v_call():
    a = ACls(str, CallValidation(str.strip))
    a('hi  ', 'hi')
    a('  a  ', 'a')
    a('   ', '')
    a('hi', 'hi')
