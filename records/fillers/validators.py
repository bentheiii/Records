from typing import Generic, TypeVar, Callable, Mapping, Optional


class ValidationToken:
    pass


T = TypeVar('T')


class ValidatorFunction(ValidationToken, Generic[T]):
    def __init__(self, func: Callable[..., T], **kwargs):
        self.func = func
        self.kwargs = kwargs

    def __call__(self, v):
        return self.func(v, **self.kwargs)


class MapValidation(ValidationToken, Generic[T]):
    def __init__(self, value_map: Optional[Mapping[T, T]] = None,
                 factory_map: Optional[Mapping[T, Callable[[], T]]] = None,
                 pass_missing = True):
        self.value_map = value_map or {}
        self.factory_map = factory_map or {}
        self.pass_missing = pass_missing

    def __call__(self, v):
        if v in self.value_map:
            return self.value_map[v]
        if v in self.factory_map:
            return self.factory_map[v]()
        if self.pass_missing:
            return v
        raise TypeError
