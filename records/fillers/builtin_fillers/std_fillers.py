from abc import abstractmethod, ABC
from functools import partial
from inspect import isabstract
from math import isclose
from numbers import Rational, Real, Complex
from typing import Any, Callable, Dict, Generic, Type, TypeVar

from records.fillers.builtin_fillers.recurse import GetFiller
from records.fillers.coercers import CoercionToken, GlobalCoercionToken
from records.fillers.filler import AnnotatedFiller, TypeCheckStyle, TypeMatch

T = TypeVar('T')


class Eval(GlobalCoercionToken):
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.kwargs.update(
            (k.__name__, k) for k in args
        )

    def __call__(self, origin, filler):
        def ret(v):
            if not isinstance(v, str):
                raise TypeError
            try:
                ret = eval(v, {'__builtins__': self.kwargs})
            except Exception as e:
                raise TypeError from e

            return ret

        return ret


class OriginDependant(GlobalCoercionToken, ABC):
    @abstractmethod
    def func(self, origin, v):
        pass

    def __call__(self, origin, filler):
        return partial(self.func, origin)


class ArgsOriginDependant(OriginDependant, ABC):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    @staticmethod
    @abstractmethod
    def func_args(origin, v, args, kwargs):
        pass

    def func(self, origin, v):
        return self.func_args(origin, v, self.args, self.kwargs)


class LooseMixin(ArgsOriginDependant, ABC):
    def __call__(self, origin, filler):
        if (not isinstance(origin, type)) or isabstract(origin):
            raise TypeError(f'cannot use loose coercer with non-concrete type {origin}')
        return super().__call__(origin, filler)


class Loose(LooseMixin):
    @staticmethod
    def func_args(origin, v, args, kwargs):
        return origin(v, *args, **kwargs)


class LooseUnpack(LooseMixin):
    @staticmethod
    def func_args(origin, v, args, kwargs):
        return origin(*v, *args, **kwargs)


class LooseUnpackMap(LooseMixin):
    @staticmethod
    def func_args(origin, v, args, kwargs):
        return origin(*args, **v, **kwargs)


class SimpleFiller(AnnotatedFiller[T], Generic[T]):
    def type_check(self, v):
        if type(v) == self.origin:
            return TypeMatch.exact
        return TypeMatch.inexact if isinstance(v, self.origin) else None

    def bind(self, owner_cls):
        super().bind(owner_cls)

        if self.type_checking_style == TypeCheckStyle.check_strict and isabstract(self.origin):
            raise TypeError(f'cannot create strict checker for abstract class {self.origin}')


class Whole(ArgsOriginDependant):
    @classmethod
    def func_args(cls, origin, v, args, kwargs):
        if isinstance(v, Rational):
            if v.denominator == 1:
                return origin(v.numerator, *args, **kwargs)
        elif isinstance(v, Real):
            mod = v % 1
            if isclose(mod, 0) or isclose(mod, 1):
                return origin(v, *args, **kwargs)
        elif isinstance(v, Complex):
            if v.imag == 0:
                return cls.func_args(origin, v.real, args, kwargs)
        raise TypeError


class ToBytes(ArgsOriginDependant):
    @staticmethod
    def func_args(origin, v, args, kwargs):
        if not isinstance(v, int):
            raise type
        if not args and ('length' not in kwargs):
            signed = kwargs.get('signed', False)
            args = ((v.bit_length() + 7 + signed) // 8,)
        return origin(v.to_bytes(*args, **kwargs))


class FromInteger(CoercionToken):
    pass


class BoolFiller(SimpleFiller[bool]):
    @staticmethod
    def _bool_from_int(v):
        if v == 0:
            return False
        if v == 1:
            return True
        raise TypeError

    def get_coercer(self, token):
        if isinstance(token, FromInteger):
            return self._bool_from_int
        return super().get_coercer(token)


class SingletonFromFalsish(ArgsOriginDependant):
    @staticmethod
    def func_args(origin, v, args, kwargs):
        if not v:
            return origin(*args, **kwargs)
        raise TypeError


class NoneFiller(SimpleFiller[None]):
    def type_check(self, v) -> bool:
        return (v is None) and TypeMatch.exact


class EllipsisFiller(SimpleFiller[type(...)]):
    def type_check(self, v) -> bool:
        return (v is ...) and TypeMatch.exact

    type_check_strict = type_check


class Encoding(Loose):
    def __init__(self, encoding, **kwargs):
        super().__init__(encoding=encoding, **kwargs)


class CallableFiller(AnnotatedFiller[Callable]):
    def type_check(self, v):
        return callable(v) and TypeMatch.exact


std_filler_map: Dict[Any, Type[AnnotatedFiller]] = {
    bool: BoolFiller,
    type(None): NoneFiller,
    object: SimpleFiller,
    type(...): EllipsisFiller
}

std_filler_checkers = []


@std_filler_checkers.append
def callable_checker(stored_type):
    if stored_type is callable:
        return CallableFiller


@std_filler_checkers.append
def none_checker(stored_type):
    if stored_type is None:
        raise GetFiller(type(None))
