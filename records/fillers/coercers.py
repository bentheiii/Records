from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Mapping, Optional, TypeVar, Type, Union


class CoercionToken:
    pass


T = TypeVar('T')


class GlobalCoercionToken(CoercionToken, ABC):
    @abstractmethod
    def __call__(self, stored_type: Type[T], filler) -> Callable[[Any], T]:
        pass


class CallCoercion(GlobalCoercionToken, Generic[T]):
    def __init__(self, func: Callable[..., T], *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def inner(self, v):
        return self.func(v, *self.args, **self.kwargs)

    def __call__(self, *_):
        return self.inner


class MapCoercion(GlobalCoercionToken, Generic[T]):
    def __init__(self, value_map: Optional[Mapping[Any, T]] = None,
                 factory_map: Optional[Mapping[Any, Callable[[], T]]] = None):
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
    def __init__(self, method: str, *args, **kwargs):
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def __call__(self, cls, filler):
        func = getattr(cls, self.method)

        def ret(v):
            return func(v, *self.args, **self.kwargs)

        return ret


class ComposeCoercer(GlobalCoercionToken):
    def __init__(self, *inner_coercers: Union[Type[CoercionToken], CoercionToken]):
        self.inner_coercers = inner_coercers

    def __call__(self, cls, filler):
        functors = [filler.get_coercer(t) for t in self.inner_coercers]
        functors.reverse()

        def ret(v):
            for f in functors:
                v = f(v)
            return v

        return ret