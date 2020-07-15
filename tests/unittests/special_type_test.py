from typing import List

from pytest import fixture, raises

from records import RecordBase


@fixture(params=[True, False], ids=['frozen', 'mutable'])
def Bits(request):
    class Bits(RecordBase, frozen=request.param):
        b: List[bool]

    Bits.__qualname__ = 'Bits'

    return Bits


def test_create_bits(Bits):
    Bits([])
    Bits(b=[0, 1, 2])
    with raises(TypeError):
        Bits(25, b=36)
