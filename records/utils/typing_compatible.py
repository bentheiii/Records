import sys
from functools import partial
from typing import get_type_hints, Callable

if sys.version_info >= (3, 8, 0):  # pragma: no cover
    from typing import get_args, get_origin
else:  # pragma: no cover
    from operator import attrgetter

    get_origin = attrgetter('__origin__')
    get_args = attrgetter('__args__')  # todo callable needs special case

if sys.version_info >= (3, 9, 0):  # pragma: no cover
    from typing import Annotated, _AnnotatedAlias

    get_type_hints = partial(get_type_hints, include_extras=True)

    def is_annotation(t):
        return isinstance(t, _AnnotatedAlias)
else:  # pragma: no cover
    class Annotated:
        def __init__(self, origin, *args):
            self.__origin__ = origin
            self.__args__ = args

        def __class_getitem__(cls, item):
            return cls(*item)

        def __call__(self, *args, **kwargs):
            raise TypeError

    Annotated.__origin__ = Annotated

    def is_annotation(t):
        return isinstance(t, Annotated)

    if sys.version_info >= (3, 8, 0):  # pragma: no cover
        _origins = get_origin
        _args = get_args

        def get_origin(v):
            return _origins(v) or getattr(v, '__origin__', None)

        def get_args(v):
            if v is Callable:
                return ()
            return _args(v) or getattr(v, '__args__', None)

__all__ = ['get_args', 'get_origin', 'Annotated', 'get_type_hints', 'is_annotation']