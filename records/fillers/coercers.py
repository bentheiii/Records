from typing import Callable, Any, TypeVar, Generic, Optional, Mapping


class CoercionToken:
    pass


T = TypeVar('T')


class CoercerFunction(CoercionToken, Generic[T]):
    def __init__(self, func: Callable[..., T], *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, v):
        return self.func(v, *self.args, **self.kwargs)


class MapCoercion(CoercionToken, Generic[T]):
    def __init__(self, value_map: Optional[Mapping[Any, T]] = None,
                 factory_map: Optional[Mapping[Any, Callable[[], T]]] = None):
        self.value_map = value_map or {}
        self.factory_map = factory_map or {}

    def __call__(self, v):
        if v in self.value_map:
            return self.value_map[v]
        if v in self.factory_map:
            return self.factory_map[v]()
        raise TypeError
