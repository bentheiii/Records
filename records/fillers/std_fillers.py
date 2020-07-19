from operator import index
from typing import Generic, TypeVar

from records.fillers.validator import AnnotatedFiller

T = TypeVar('T')


class SimpleFiller(AnnotatedFiller[T], Generic[T]):
    def type_check_strict(self, v) -> bool:
        return type(v) == self.origin

    def type_check(self, v) -> bool:
        return isinstance(v, self.origin)


class IntFiller(SimpleFiller[int]):
    def coerce(self, v) -> int:
        if isinstance(v, str):
            return int(v)
        return index(v)


class BoolFiller(SimpleFiller[bool]):
    def coerce(self, v) -> bool:
        if isinstance(v, int):
            if v == 0:
                return False


class FloatFiller(SimpleFiller[float]):
    def coerce(self, v) -> float:
        return float(v)


std_map = {
    int: IntValidator,
    float: FloatValidator

}
