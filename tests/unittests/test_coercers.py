from pytest import raises

from records import Annotated, Eval, Loose, RecordBase, TypeCheckStyle
from records.fillers import ComposeCoercer


def ACls(T, *args):
    class A(RecordBase):
        x: Annotated[T, TypeCheckStyle.check, args]

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