from typing import Optional, Type, TypeVar

T = TypeVar('T')


def _as_instance(obj, cls: Type[T]) -> Optional[T]:
    """
    Check that an object is of a type, or construct if it is a class.
    :param obj: The object to check and coerce.
    :param cls: The target class to check against.
    :return: `obj`, if it is an instance of `cls`, `obj()` if it is a subclass of `cls`, or `None` otherwise.
    """
    if isinstance(obj, cls):
        return obj
    elif isinstance(obj, type) and issubclass(obj, cls):
        return obj()
    wrapped = getattr(obj, '__wrapped__', None)
    if wrapped is not None:
        return obj()
    return None
