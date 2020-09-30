from dataclasses import dataclass

from records import RecordBase
from tests.benchmarking.util import Benchmark

bm = Benchmark('construction')


class REC_Point(RecordBase):
    x: float
    y: float
    z: int = 0
    w: str = ""


@bm.measure(source=(REC_Point, ...))
def new_record():
    REC_Point(x=12, y=3, w="hi")


@dataclass
class PYD_Point:
    x: float
    y: float
    z: int = 0
    w: str = ""


@bm.measure(source=(PYD_Point, ...))
def new_dataclass():
    PYD_Point(x=12, y=3, w="hi")


if __name__ == '__main__':
    print(bm.summary())
