from numbers import Number
from typing import Dict, Iterable, List, Sequence, Tuple, Type, Union

from pytest import mark, raises

from records import Annotated, RecordBase, TypeCheckStyle

try:
    from typing import Literal
except ImportError:
    Literal = None


def ACls(T):
    class A(RecordBase):
        x: Annotated[T, TypeCheckStyle.check_strict]

    return A


def test_str():
    A = ACls(str)

    a = A('a')
    assert a.x == 'a'
    with raises(TypeError):
        A(12)


def test_int():
    A = ACls(int)

    a = A(12)
    assert a.x == 12
    with raises(TypeError):
        A(False)
    with raises(TypeError):
        A(2.0)


def test_iterable():
    with raises(TypeError):
        ACls(Iterable[str])


def test_list_strict():
    with raises(TypeError):
        ACls(Sequence[Annotated[str, TypeCheckStyle.check_strict]])


@mark.skipif(Literal is None, reason='Literal cannot be imported')
def test_literal():
    A = ACls(Literal['a', 'b', 2, 0])
    a = A('b')
    assert a.x == 'b'
    a = A('a')
    assert a.x == 'a'
    a = A(2)
    assert a.x == 2
    with raises(ValueError):
        A('2')
    with raises(TypeError):
        A(2.3)
    with raises(TypeError):
        A(False)


@mark.parametrize('T', [None, type(None)])
def test_none(T):
    A = ACls(T)
    a = A(None)
    assert a.x is None
    with raises(TypeError):
        A('None')
    with raises(TypeError):
        A(False)


def test_union1():
    A = ACls(Union[int, str])
    a = A(12)
    assert a.x == 12
    a = A(15)
    assert a.x == 15
    a = A('2')
    assert a.x == '2'
    with raises(TypeError):
        A(True)
    with raises(TypeError):
        A(2.3)


def test_union2():
    class T0:
        pass

    class T1(T0):
        pass

    class T2(T1):
        pass

    A = ACls(Union[T0, T1])
    A(T0())
    A(T1())
    with raises(TypeError):
        A(T2())
    with raises(TypeError):
        A(2.3)


def test_nested():
    A = ACls(List[List[Number]])
    a = A([[2.0, 3, 6], [1, 2, 3], [-9, 5, 6]])
    assert a.x == [[2.0, 3, 6], [1, 2, 3], [-9, 5, 6]]


def test_type():
    A = ACls(Type[Exception])
    a = A(Exception)
    assert a.x is Exception
    a = A(TypeError)
    assert a.x is TypeError
    with raises(ValueError):
        A(BaseException)
    with raises(TypeError):
        A(156)

    class M(type):
        pass

    class E(Exception, metaclass=M):
        pass

    with raises(TypeError):
        A(E)


def test_tuple_reg():
    A = ACls(Tuple[Annotated[int, TypeCheckStyle.check_strict], Annotated[str, TypeCheckStyle.check_strict]])
    a = A((5, '6'))
    assert a.x == (5, '6')
    a = A((9, '3'))
    assert a.x == (9, '3')
    with raises(TypeError):
        A(56)
    with raises(TypeError):
        A(('3', 3))
    with raises(ValueError):
        A((3, '3', None))
    with raises(ValueError):
        A((3,))
    with raises(TypeError):
        A((True, '9'))


def test_tuple_variadic():
    A = ACls(Tuple[Annotated[int, TypeCheckStyle.check_strict], ...])
    a = A((5, 6))
    assert a.x == (5, 6)
    a = A((9, 3, 7))
    assert a.x == (9, 3, 7)
    a = A(())
    assert a.x == ()
    with raises(TypeError):
        A(56)
    with raises(TypeError):
        A(('3', 3))
    with raises(TypeError):
        A((True, 3))


def test_invalid_tuple():
    with raises(TypeError):
        class _(RecordBase):
            x: Tuple[Annotated[str, TypeCheckStyle.check_strict], int]
    with raises(TypeError):
        class _(RecordBase):
            x: Tuple[Annotated[str, TypeCheckStyle.check_strict], ...]


def test_invalid_dict():
    with raises(TypeError):
        class A(RecordBase):
            x: Dict[Annotated[str, TypeCheckStyle.check_strict], int]


def test_invalid_geniter():
    with raises(TypeError):
        class A(RecordBase):
            x: List[Annotated[str, TypeCheckStyle.check_strict]]


def test_dict():
    A = ACls(Dict[Annotated[int, TypeCheckStyle.check_strict], int])
    a = A({5: '6'})
    assert a.x == {5: '6'}
    a = A({})
    assert a.x == {}
    with raises(TypeError):
        A(56)
    with raises(TypeError):
        A({'3': 3})
    with raises(TypeError):
        A({False: 3})


def test_invalid_gen1():
    with raises(TypeError):
        class A(RecordBase):
            x: Iterable[Annotated[str, TypeCheckStyle.check]]
