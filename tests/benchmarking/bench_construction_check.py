from pydantic import BaseModel

from records import RecordBase, check_strict
from tests.benchmarking.util import Benchmark

bm = Benchmark('construction_checked')


class REC_Point(RecordBase, default_type_check=check_strict):
    x: float
    y: float
    z: int = 0
    w: str = ""


@bm.measure(source=(REC_Point, ...), highlight=True)
def new_record():
    REC_Point(x=12.1, y=3.0, w="hi")


class PYD_Point(BaseModel):
    x: float
    y: float
    z: int = 0
    w: str = ""


@bm.measure(source=(PYD_Point, ...))
def new_pydantic():
    PYD_Point(x=12, y=3, w="hi")


if __name__ == '__main__':
    print(bm.rst())
