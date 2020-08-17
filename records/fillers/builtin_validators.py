import re
from typing import Any, Union

from records.fillers.validators import AssertValidation, GlobalValidationToken


class _Least:  # pragma: no cover
    def __lt__(self, other):
        return True

    def __le__(self, other):
        return True

    def __gt__(self, other):
        return False

    def __ge__(self, other):
        return self == other


class _Greatest:  # pragma: no cover
    def __lt__(self, other):
        return False

    def __le__(self, other):
        return self == other

    def __gt__(self, other):
        return True

    def __ge__(self, other):
        return True


least = _Least()
greatest = _Greatest()


class Clamp(GlobalValidationToken):
    def __init__(self, ge: Any = least, le: Any = greatest, **kwargs):
        super().__init__(**kwargs)
        self.ge = ge
        self.le = le

    def inner(self, v):
        return min(max(v, self.ge), self.le)

    def __call__(self, *_):
        return self.inner


class Cyclic(GlobalValidationToken):
    def __init__(self, minimum, maximum, **kwargs):
        super().__init__(**kwargs)
        self.minimum = minimum
        self.maximum = maximum

    def inner(self, v):
        if self.minimum <= v <= self.maximum:
            return v
        d = v - self.minimum
        d %= (self.maximum - self.minimum)
        return self.minimum + d

    def __call__(self, *_):
        return self.inner


class Within(AssertValidation):
    def __init__(self, ge: Any = least, lt: Any = greatest, g_eq=True, l_eq=False, **kwargs):
        super().__init__(**kwargs)
        self.ge = ge
        self.lt = lt
        self.g_eq = g_eq
        self.l_eq = l_eq

    def assert_(self, v) -> bool:
        if self.g_eq:
            if not (self.ge <= v):
                return False
        else:
            if not (self.ge < v):
                return False

        if self.l_eq:
            if not (self.lt >= v):
                return False
        else:
            if not (self.lt > v):
                return False

        return True


class FullMatch(AssertValidation):
    def __init__(self, pattern: Union[re.Pattern, str], **kwargs):
        super().__init__(**kwargs)
        self.pattern = re.compile(pattern)

    def assert_(self, v) -> bool:
        return bool(self.pattern.fullmatch(v))


class Truth(AssertValidation):
    def assert_(self, v) -> bool:
        return bool(v)
