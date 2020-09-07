from typing import Any, Pattern, Union

import records.extras as extras
from records.fillers.validators import AssertValidation, GlobalValidationToken


class _Least:  # pragma: no cover
    """
    A simple object that is always less than any other object
    """

    def __lt__(self, other):
        return True

    def __le__(self, other):
        return True

    def __gt__(self, other):
        return False

    def __ge__(self, other):
        return self == other


class _Greatest:  # pragma: no cover
    """
    A simple object that is always greater than any other object
    """

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
    """
    A validator class that constrains the value to be between two bounds, bringing it to the nearest bound if it
     falls outside.
    """

    def __init__(self, ge: Any = least, le: Any = greatest, **kwargs):
        """
        :param ge: the lower bound, defaults to no lower bound
        :param le: the upper bound, defaults to no upper bound
        """
        super().__init__(**kwargs)
        self.ge = ge
        self.le = le
        if self.ge > self.le:
            raise ValueError('the lower bound must not be greater then the upper bound')

    def inner(self, v):
        return min(max(v, self.ge), self.le)

    def __call__(self, *_):
        return self.inner


class Cyclic(GlobalValidationToken):
    """
   A validator class that constrains the value to be between two bounds, bringing it to the equivalent position as
    though the domain is cyclic. Useful for angles and time of day.
   """

    def __init__(self, minimum, maximum, **kwargs):
        """
        :param minimum: the inclusive lower bound
        :param maximum: the exclusive upper bound.
        """
        super().__init__(**kwargs)
        self.minimum = minimum
        self.maximum = maximum

    def inner(self, v):
        if self.minimum <= v < self.maximum:
            return v
        d = v - self.minimum
        d %= (self.maximum - self.minimum)
        return self.minimum + d

    def __call__(self, *_):
        return self.inner


class Within(AssertValidation):
    """
    An assertion validation that raises an error if the value falls outside of bounds.
    """

    def __init__(self, ge: Any = least, lt: Any = greatest, g_eq=True, l_eq=False, **kwargs):
        """
        :param ge: the lower bound, defaults to no lower bound
        :param le: the upper bound, defaults to no upper bound
        :param g_eq: whether the lower bound is inclusive, defaults to True.
        :param l_eq: whether the upper bound is inclusive, defaults to False.
        :param kwargs: forwarded to `AssertValidation`_
        """
        super().__init__(**kwargs)
        self.ge = ge
        self.lt = lt
        self.g_eq = g_eq
        self.l_eq = l_eq
        if ge > lt or ((not g_eq or not l_eq) and ge == lt):
            raise ValueError('the lower bound must not be greater then the upper bound')

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
    """
    An assertion validation that raises an error if the value does not match a regex pattern.
    """

    def __init__(self, pattern: Union[Pattern, str, bytes], **kwargs):
        """
        :param pattern: either a compiled pattern or an uncompiled string or bytestring
        :param kwargs: forwarded to `AssertValidation`_
        .. note::
            ``pattern`` will be compiled in accordance to `records.extras.re`_
        """
        super().__init__(**kwargs)
        self.pattern = extras.re.compile(pattern)

    def assert_(self, v) -> bool:
        return bool(self.pattern.fullmatch(v))


class Truth(AssertValidation):
    """
    An assertion validation that raises an error if the value does not evaluate as True.
    """

    def assert_(self, v) -> bool:
        return bool(v)
