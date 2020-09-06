from abc import ABC, abstractmethod
from ast import literal_eval
from functools import partial
from inspect import isabstract
from math import isclose
from numbers import Complex, Rational, Real, Integral
from typing import Any, Callable, Dict, Generic, Type, TypeVar

from records.fillers.builtin_fillers.recurse import GetFiller
from records.fillers.coercers import CoercionToken, GlobalCoercionToken
from records.fillers.filler import AnnotatedFiller, TypeCheckStyle, TypeMatch

T = TypeVar('T')


class Eval(GlobalCoercionToken):
    """
    A coercion token to evaluate a string input as a python expression using `eval`
    .. warning::
        evaluating arbitrary strings is always risky!
    """

    def __init__(self, *args, **kwargs):
        if args and args[0] is ...:
            self.add_bound = True
            args = args[1:]
        else:
            self.add_bound = False
        self.kwargs = kwargs
        self.kwargs.update(
            (k.__name__, k) for k in args
        )

    def __call__(self, origin, filler):
        ns = self.kwargs
        if self.add_bound:
            ns = {**self.kwargs, origin.__name__: origin}

        def ret(v):
            if not isinstance(v, str):
                raise TypeError
            try:
                ret = eval(v, {'__builtins__': ns})
            except Exception as e:
                raise TypeError from e

            return ret

        return ret


class LiteralEval(GlobalCoercionToken):
    """
    A coercion token to evaluate string inputs as literals continuously
    """

    def __call__(self, origin, filler):
        if origin not in {int, str, float, complex, set, tuple, dict, list, bool}:
            raise TypeError(f'cannot use literal evaluation coercer with non-literal type {origin}')

        def ret(v):
            while isinstance(v, str):
                v = literal_eval(v)
            return v

        return ret


class OriginDependant(GlobalCoercionToken, ABC):
    """
    A convenience coercion token superclass to pass coercion directly to a token method
    """

    def __init__(self, *args, **kwargs):
        """
        :param args: arguments accessible to the callback
        :param kwargs: keywords accessible to the callback
        """
        self.args = args
        self.kwargs = kwargs

    @staticmethod
    @abstractmethod
    def func_args(origin, v):
        """
        The coercion callback to apply on an argument, given an origin.
        :param origin: The target storage type.
        :param v: The input argument to the coercer.
        :return: The coerced value
        """
        pass

    def __call__(self, origin, filler):
        return partial(self.func_args, origin)


class LooseMixin(OriginDependant, ABC):
    """
    A superclass for "loose" coercion tokens that call the class constructor, forbidding binding to abstract classes
    """
    def __call__(self, origin, filler):
        if (not isinstance(origin, type)) or isabstract(origin):
            raise TypeError(f'cannot use loose coercer with non-concrete type {origin}')
        return super().__call__(origin, filler)


class Loose(LooseMixin):
    """
    A coercion token to call the class constructor with the input as an argument
    """
    def func_args(self, origin, v):
        return origin(v, *self.args, **self.kwargs)


class LooseUnpack(LooseMixin):
    """
    A coercion token to call the class constructor with the input as an unpacked iterable
    """
    def func_args(self, origin, v):
        return origin(*v, *self.args, **self.kwargs)


class LooseUnpackMap(LooseMixin):
    """
    A coercion token to call the class constructor with the input as an unpacked mapping
    """
    def func_args(self, origin, v):
        return origin(*self.args, **v, **self.kwargs)


class SimpleFiller(AnnotatedFiller[T], Generic[T]):
    """
    A concrete filler class that uses instance checking to check types
    """
    def type_check(self, v):
        if type(v) == self.origin:
            return TypeMatch.exact
        return TypeMatch.inexact if isinstance(v, self.origin) else None

    def bind(self, owner_cls):
        super().bind(owner_cls)

        if self.type_checking_style == TypeCheckStyle.check_strict and isabstract(self.origin):
            raise TypeError(f'cannot create strict checker for abstract class {self.origin}')


class Whole(OriginDependant):
    """
    A coercion token to attempt to convert a whole Number to an Integer type
    """
    def func_args(self, origin, v):
        if isinstance(v, Rational):
            if v.denominator == 1:
                return origin(v.numerator, *self.args, **self.kwargs)
        elif isinstance(v, Real):
            mod = v % 1
            if isclose(mod, 0) or isclose(mod, 1):
                return origin(v, *self.args, **self.kwargs)
        elif isinstance(v, Complex):
            if v.imag == 0:
                return self.func_args(origin, v.real)
        raise TypeError


class ToBytes(OriginDependant):
    """
    A coercion token to convert a n Integer value to a bytestring
    """
    def func_args(self, origin, v):
        # In theory we aught to restrict this token to just ints, but if another Integer subclass wants to use this
        # coercer we aren't gonna stop them
        if not isinstance(v, Integral):
            raise type
        if not self.args and ('length' not in self.kwargs):
            signed = self.kwargs.get('signed', False)
            args = ((v.bit_length() + 7 + signed) // 8,)
        else:
            args = self.args
        return origin(v.to_bytes(*args, **self.kwargs))


class FromInteger(CoercionToken):
    """
    A coercion token to convert an integer to a boolean, failing if the value is not 0 or 1.
    """
    pass


class BoolFiller(SimpleFiller[bool]):
    """
    A specialized boolean filler to handle `FromInteger`
    """
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


class Falsish(OriginDependant):
    """
    A coercion token to construct an instance of the target type ignoring the input, only if the argument is falsish.
     Useful to create empty objects from None inputs.
    """
    def func_args(self, origin, v):
        if not v:
            return origin(*self.args, **self.kwargs)
        raise TypeError


class NoneFiller(SimpleFiller[None]):
    """
    A specialized filler for None
    """
    def type_check(self, v) -> bool:
        return (v is None) and TypeMatch.exact


class EllipsisFiller(SimpleFiller[type(...)]):
    """
    A specialized filler for Ellipsis
    """
    def type_check(self, v) -> bool:
        return (v is ...) and TypeMatch.exact


class CallableFiller(AnnotatedFiller[Callable]):
    """
    A specialized filler for callable objects
    """
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
        return GetFiller(type(None))
