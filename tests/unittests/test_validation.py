from typing import Iterable, Any, Union
from unittest.mock import Mock

from pytest import raises, mark, warns

from records import Annotated, Loose, RecordBase, TypeCheckStyle, Within, Clamp, Cyclic, \
    FullMatch, Truth, AssertCallValidation, CallValidation, check


def ACls(T, *args):
    class A(RecordBase):
        x: Annotated.__class_getitem__((T, TypeCheckStyle.check, *args))

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


def test_char():
    class A(RecordBase):
        c: Annotated[Union[str, bytes], check]

        @classmethod
        def pre_bind(cls):
            super().pre_bind()

            @cls.c.add_assert_validator
            def is_char(v):
                return len(v) == 1

    assert A('1').c == '1'
    assert A(b'x').c == b'x'
    with raises(ValueError):
        A('12')

def test_char_var():
    class A(RecordBase):
        c: Annotated[str, check]

        @classmethod
        def pre_bind(cls):
            super().pre_bind()

            @cls.c.add_assert_validator(err=LookupError)
            def is_char(v):
                return len(v) == 1

    assert A('1').c == '1'
    assert A('x').c == 'x'
    with raises(ValueError):
        A('12')


def test_censor():
    class A(RecordBase):
        x: Annotated[str, check]

        @classmethod
        def pre_bind(cls):
            super().pre_bind()

            @cls.x.add_validator
            def censor(v: str):
                return v.replace('poop', '****')

    assert A('foo').x == 'foo'
    assert A('poopy').x == '****y'


def test_hex():
    class A(RecordBase):
        x: Annotated[int, check]

        @classmethod
        def pre_bind(cls):
            super().pre_bind()

            @cls.x.add_coercer
            def from_hex(v: str):
                if isinstance(v, str) or v.startswith('0x'):
                    return int(v, 16)
                raise TypeError

    assert A(15).x == 15
    assert A('0xff').x == 255


def test_post_new_modify():
    class A(RecordBase, default_type_check=check):
        a: int
        b: int
        c: int

        def post_new(self):
            self.a, self.b, self.c = sorted([self.a, self.b, self.c])

        def __iter__(self):
            yield from [self.a, self.b, self.c]

    assert list(A(a=3, b=0, c=12)) == [0, 3, 12]


def test_post_new_check():
    class A(RecordBase, default_type_check=check):
        a: int
        b: int
        c: int

        def post_new(self):
            assert self.a <= self.b <= self.c

        def __iter__(self):
            yield from [self.a, self.b, self.c]

    assert list(A(a=0, b=3, c=12)) == [0, 3, 12]

    with raises(AssertionError):
        A(a=4, b=3, c=12)
