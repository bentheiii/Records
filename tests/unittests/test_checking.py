from numbers import Number
from typing import Dict, Iterable, List, Literal, Mapping, Sequence, Tuple, Type, Union

from pytest import mark, raises

from records import Annotated, RecordBase, TypeCheckStyle


def ACls(T):
    class A(RecordBase):
        x: Annotated[T, TypeCheckStyle.check]

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
    a = A(False)
    assert a.x is False
    with raises(TypeError):
        A(2.0)


def test_iterable():
    A = ACls(Iterable[str])

    a = A('12')
    assert a.x == '12'
    a = A(('a', 'b', 'c'))
    assert a.x == ('a', 'b', 'c')
    a = A(str(i) for i in range(4))
    assert list(a.x) == ['0', '1', '2', '3']
    a = A(range(4))
    assert list(a.x) == [0, 1, 2, 3]
    with raises(TypeError):
        A(123)


def test_list_strict():
    A = ACls(Sequence[Annotated[str, TypeCheckStyle.check]])

    a = A('12')
    assert a.x == '12'
    a = A(('a', 'b', 'c'))
    assert a.x == ('a', 'b', 'c')
    a = A([str(i) for i in range(4)])
    assert a.x == ['0', '1', '2', '3']
    with raises(TypeError):
        A(123)
    with raises(TypeError):
        A(range(12))


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
    with raises(ValueError):
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


def test_union():
    A = ACls(Union[int, bool])
    a = A(12)
    assert a.x == 12
    a = A(15)
    assert a.x == 15
    a = A(True)
    assert a.x is True
    with raises(TypeError):
        A('2')
    with raises(TypeError):
        A(2.3)


def test_invalid_unions():
    with raises(TypeError):
        class A(RecordBase):
            x: Union[Annotated[str, TypeCheckStyle.check], int]


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


def test_tuple_reg():
    A = ACls(Tuple[Annotated[int, TypeCheckStyle.check], Annotated[str, TypeCheckStyle.check]])
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


def test_tuple_variadic():
    A = ACls(Tuple[Annotated[int, TypeCheckStyle.check], ...])
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


def test_invalid_tuple():
    with raises(TypeError):
        class _(RecordBase):
            x: Tuple[Annotated[str, TypeCheckStyle.check], int]
    with raises(TypeError):
        class _(RecordBase):
            x: Tuple[Annotated[str, TypeCheckStyle.check], ...]


def test_invalid_dict():
    with raises(TypeError):
        class A(RecordBase):
            x: Dict[Annotated[str, TypeCheckStyle.check], int]


def test_invalid_geniter():
    with raises(TypeError):
        class A(RecordBase):
            x: List[Annotated[str, TypeCheckStyle.check]]


def test_dict():
    A = ACls(Mapping[Annotated[int, TypeCheckStyle.check], int])
    a = A({5: '6'})
    assert a.x == {5: '6'}
    a = A({})
    assert a.x == {}
    with raises(TypeError):
        A(56)
    with raises(TypeError):
        A({'3': 3})


def test_invalid_gen1():
    with raises(TypeError):
        class A(RecordBase):
            x: Iterable[Annotated[str, TypeCheckStyle.check]]
