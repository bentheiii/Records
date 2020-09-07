from abc import ABC, abstractmethod
from ast import literal_eval
from functools import partial, wraps
from inspect import isabstract
from math import isclose
from numbers import Complex, Rational, Real, Integral
from typing import Any, Callable, Dict, Generic, Type, TypeVar, Union, Tuple, Optional

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
                try:
                    v = literal_eval(v)
                except ValueError:
                    raise TypeError
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If type_constraint is set, only arguments of that type would be accepted as inputs
        self._type_constraint: Union[None, type, Tuple[type, ...]] = None

    def func_args(self, origin, v):
        if self._type_constraint and not isinstance(v, self._type_constraint):
            raise TypeError(f'must be of type {self._type_constraint}')
        return origin(v, *self.args, **self.kwargs)

    @classmethod
    def constrain(cls, item: Union[type, Tuple[type, ...]]):
        """
        Can be used to constrain Loose to only accept specific inputs of specific types.
        :param item: the type or types to constrain inputs by.
        :return: a factory function to a constrained Loose token.
        """
        # here we check that the item can indeed by used for type checking
        # we need to thoroughly check the input type here since if there's an error during coercion,
        # we won't know about it
        isinstance(None, item)

        @wraps(cls)
        def factory(*args, **kwargs):
            ret = cls(*args, **kwargs)
            ret._type_constraint = item
            return ret

        return factory


class LooseUnpack(LooseMixin):
    """
    A coercion token to call the class constructor with the input as an unpacked iterable
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If type_constraint is set, only arguments of that type would be accepted as inputs
        self._type_constraints: Union[None, Tuple[Union[type, Tuple[type, ...]], ...],
                                      Tuple[Union[type, Tuple[type, ...]], type(...)]] = None

    def func_args(self, origin, v):
        if self._type_constraints is not None:
            v = tuple(v)
            if len(self._type_constraints) == 2 and self._type_constraints[1] is ...:
                if any(not isinstance(i, self._type_constraints[0]) for i in v):
                    raise TypeError(f'all arguments must be instances of {self._type_constraints[0]}')
            else:
                if len(v) != len(self._type_constraints) \
                        or any(not isinstance(i, tc) for (i, tc) in zip(v, self._type_constraints)):
                    raise TypeError
        return origin(*v, *self.args, **self.kwargs)

    @classmethod
    def constrain(cls, *items: Union[type, Tuple[type, ...], type(...)]):
        """
        Can be used to constrain LooseUnpack to only accept specific inputs of specific types.
        :param items: the type or types to constrain inputs by.
        :return: a factory function to a constrained LooseUnpack token.
        """
        # here we check that the item can indeed by used for type checking
        if len(items) == 2 and items[1] is ...:
            isinstance(None, items[0])
        else:
            for i in items:
                isinstance(None, i)

        @wraps(cls)
        def factory(*args, **kwargs):
            ret = cls(*args, **kwargs)
            ret._type_constraints = items
            return ret

        return factory


class LooseUnpackMap(LooseMixin):
    """
    A coercion token to call the class constructor with the input as an unpacked mapping
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If type_constraint is set, only arguments of that type would be accepted as inputs
        self._type_constraints: Optional[Dict[str, Union[type, Tuple[type, ...]]]] = None

    def func_args(self, origin, v):
        if self._type_constraints is not None:
            for k, a in v.items():
                tc = self._type_constraints.get(k)
                if tc is None or not isinstance(a, tc):
                    raise TypeError
        return origin(*self.args, **v, **self.kwargs)

    @classmethod
    def constrain(cls, **items: Union[type, Tuple[type, ...]]):
        """
        Can be used to constrain LooseUnpackMap to only accept specific inputs of specific types.
        :param items: the type or types to constrain inputs by.
        :return: a factory function to a constrained LooseUnpackMap token.
        """
        # here we check that the item can indeed by used for type checking
        for v in items.values():
            isinstance(None, v)

        @wraps(cls)
        def factory(*args, **kwargs):
            ret = cls(*args, **kwargs)
            ret._type_constraints = items
            return ret

        return factory


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
