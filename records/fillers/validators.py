from abc import abstractmethod, ABC
from logging import Logger
from typing import Callable, Generic, TypeVar, Type, Any, Union, NoReturn
import warnings


class ValidationToken:
    pass


T = TypeVar('T')


class GlobalValidationToken(ValidationToken, ABC):
    @abstractmethod
    def __call__(self, stored_type: Type[T], filler) -> Callable[[Any], T]:
        pass


class AssertValidation(GlobalValidationToken, ABC):
    def __init__(self, err: Union[str, Exception] = 'validation failed', warn: Union[bool, Logger] = False):
        self.err = err
        self.warn = warn

    def _exc(self) -> Exception:
        if isinstance(self.err, Exception):
            return self.err
        return ValueError(self.err)

    def _raise(self) -> NoReturn:
        exc = self._exc()
        if self.warn:
            if self.warn is True:
                warnings.warn(str(exc))
            else:
                self.warn.warning(str(exc))
        else:
            raise exc

    @abstractmethod
    def assert_(self, v) -> bool:
        pass

    def inner(self, v):
        if not self.assert_(v):
            self._raise()
        return v

    def __call__(self, *_):
        return self.inner


class AssertCallValidation(AssertValidation):
    def __init__(self, func: Callable[..., bool], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.func = func

    def assert_(self, v) -> bool:
        return self.func(v)


class CallValidation(GlobalValidationToken, Generic[T]):
    def __init__(self, func: Callable[..., T], *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def inner(self, v):
        return self.func(v, *self.args, **self.kwargs)

    def __call__(self, *_):
        return self.inner
