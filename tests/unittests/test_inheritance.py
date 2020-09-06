from typing import Hashable
from unittest.mock import Mock

from _pytest.recwarn import warns
from pytest import mark, raises

from records import Annotated, RecordBase, check


def test_direct_inheritance():
    class A(RecordBase):
        a: Annotated[int, check]

    class B(A):
        b: Annotated[int, check]

    b = B(a=1, b=2)
    assert b.b == 2
    assert b.a == 1
    assert isinstance(b, B)
    assert isinstance(b, A)

    a = A(a=52)
    assert a.a == 52


def test_override():
    class A(RecordBase):
        x: Annotated[int, check]

    with raises(ValueError):
        class B(A):
            x: Annotated[int, check]


def test_direct_freeze():
    class A(RecordBase, frozen=False):
        a: Annotated[int, check]

    class B(A, frozen=True):
        b: Annotated[int, check]

    b = B(a=1, b=2)
    assert b.b == 2
    assert b.a == 1

    assert not issubclass(A, Hashable)
    assert issubclass(B, Hashable)

    with raises(TypeError):
        b.a = 3


def test_direct_unfreeze():
    class A(RecordBase, frozen=True):
        a: Annotated[int, check]

    class B(A, frozen=False):
        b: Annotated[int, check]

    b = B(a=1, b=2)
    assert b.b == 2
    assert b.a == 1

    assert not issubclass(B, Hashable)
    assert issubclass(A, Hashable)

    b.a = 3
    assert b.a == 3


def test_multi():
    class A0(RecordBase):
        a0: Annotated[int, check]

    class A1(RecordBase):
        a1: Annotated[int, check]

    class B(A0, A1):
        b: Annotated[int, check]

    b = B(a0=1, a1=2, b=2)
    assert b.a0 == 1
    assert b.a1 == 2
    assert b.b == 2

    assert isinstance(b, B)
    assert isinstance(b, A0)
    assert isinstance(b, A1)


def test_multi_override():
    class A0(RecordBase):
        a: Annotated[int, check]

    class A1(RecordBase):
        a: Annotated[int, check]

    with raises(ValueError):
        class B(A0, A1):
            pass


@mark.parametrize('decl', [False, True])
def test_hybrid_mixin(decl):
    class M:
        if decl:
            x: int

        def xsq(self):
            return self.x ** 2

    class A(RecordBase, M):
        x: int

    a = A(12)

    assert a.x == 12
    assert a.xsq() == 144


@mark.parametrize('decl', [False, True])
def test_hybrid_mixin_new(decl):
    class M:
        if decl:
            x: int

        def __new__(cls):
            self = super().__new__(cls)
            self.a = "a"
            return self

        def xsq(self):
            return self.x ** 2

    class A(RecordBase, M):
        x: int

    a = A(12)

    assert a.x == 12
    assert a.xsq() == 144
    assert a.a == "a"


@mark.parametrize('decl', [False, True])
@mark.parametrize('frozen', [False, True])
def test_hybrid_mixin_init(decl, frozen):
    class M:
        if decl:
            x: int

        def __init__(self):
            self.a = "a"

        def xsq(self):
            return self.x ** 2

    class S(RecordBase):
        x: int

    with warns(UserWarning):
        class A(S, M, frozen=frozen):
            pass

    a = A(12)

    assert a.x == 12
    assert a.xsq() == 144
    assert not hasattr(a, 'a')


@mark.parametrize('decl', [False, True])
@mark.parametrize('frozen', [False, True])
def test_hybrid_mixin_init_warns(decl, frozen):
    d = Mock()

    class M:
        if decl:
            x: int

        def __init__(self):
            d()

        def xsq(self):
            return self.x ** 2

    class S(RecordBase):
        x: Annotated[int, check]

    with warns(UserWarning):
        class A(S, M, frozen=frozen, unary_parse=True):
            pass

    a = A(12)

    assert a.x == 12
    assert a.xsq() == 144
    assert d.call_count == 0
    assert A(a) == a
    assert d.call_count == 0


def test_inherit_nondestructive_check():
    class A(RecordBase):
        a: Annotated[int, check]

    class B(A):
        b: Annotated[int, check]

    assert A.a.owner == A
    assert B.a.owner == A


def test_inherit_nondestructive_validator():
    class A(RecordBase):
        a: Annotated[int, check]

    with raises(RuntimeError):
        class B(A):
            b: Annotated[int, check]

            @classmethod
            def pre_bind(cls):
                @cls.a.add_assert_validator
                def _(v):
                    return v >= 0
