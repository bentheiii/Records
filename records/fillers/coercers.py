from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Mapping, Optional, Type, TypeVar, Union

from records.fillers.util import _as_instance


class CoercionToken:
    """
    A base class for all object that should be interpreted as coercers
    """
    pass


T = TypeVar('T')


class GlobalCoercionToken(CoercionToken, ABC):
    """
    A base class for all coercers that can act on multiple kinds of fillers
    """

    @abstractmethod
    def __call__(self, stored_type: Type[T], filler) -> Callable[[Any], T]:
        """
        :param stored_type: the type the callback should return
        :param filler: the filler the coercion callback will be called from
        :return: a callable to act as a coercion callback for the specified filler
        """
        pass


class CallCoercion(GlobalCoercionToken, Generic[T]):
    """
    A coercion token to call arbitrary functions
    """

    def __init__(self, func: Callable[..., T], *args, **kwargs):
        """
        :param func: The callable to use as the coercion callback.
        :param args: Optional positional arguments to pass to ``func``, after the validation argument.
        :param kwargs: Optional keyword arguments to pass to ``func``.

        .. note::

            calling ``CallCoercion`` with ``args`` or ``kwargs`` is akin to calling it with a
            :py:func:`functools.partial` as ``func``.

            >>> CallCoercion(foo, a, b, c=d)
            >>> # is equivalent to
            >>> CallCoercion(lambda v: foo(v, a, b, c=d))
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def inner(self, v):
        return self.func(v, *self.args, **self.kwargs)

    def __call__(self, *_):
        return self.inner


class MapCoercion(GlobalCoercionToken, Generic[T]):
    """
    A coercion token to map values by arbitrary, pre-defined mappings
    """

    def __init__(self, value_map: Optional[Mapping[Any, T]] = None,
                 factory_map: Optional[Mapping[Any, Callable[[], T]]] = None):
        """
        :param value_map: a mapping to map values to coerced values
        :param factory_map: a mapping to map values to factory callbacks that create coerced values
        """
        self.value_map = value_map or {}
        self.factory_map = factory_map or {}

    def inner(self, v):
        if v in self.value_map:
            return self.value_map[v]
        if v in self.factory_map:
            return self.factory_map[v]()
        raise TypeError

    def __call__(self, *_):
        return self.inner


class ClassMethodCoercion(GlobalCoercionToken, Generic[T]):
    """
    A coercion token to call a class method in the target class
    """

    def __init__(self, method: str, *args, **kwargs):
        """
        :param method: The name of the class method to call
        :param args: Optional positional arguments to pass to the class method, after the validation argument.
        :param kwargs: Optional keyword arguments to pass to class method.
        """
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def __call__(self, cls, filler):
        func = getattr(cls, self.method)

        def ret(v):
            return func(v, *self.args, **self.kwargs)

        return ret


class ComposeCoercer(GlobalCoercionToken):
    """
    A coercion token to chain two coercion callbacks one after the other
    """

    def __init__(self, *inner_coercers: Union[Type[CoercionToken], CoercionToken]):
        """
        :param inner_coercers: an iterable of coercion tokens to apply upon the argument, in reverse order.

        .. note::
            the inner coercion callbacks are called in reverse order. So if a token ``A`` will result in callback ``a``,
            and token ``B`` will result in callback ``b``, then the token ``ComposeCoercer(A,B)`` will result in
            callback ``lambda v: a(b(v))``.
        """
        self.inner_coercers = [_as_instance(ic, CoercionToken) for ic in inner_coercers]

    def __call__(self, cls, filler):
        functors = [filler.get_coercer(t) for t in self.inner_coercers]
        functors.reverse()

        def ret(v):
            for f in functors:
                v = f(v)
            return v

        return ret
