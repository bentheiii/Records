import warnings
from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Callable, Generic, Type, TypeVar, Union


class ValidationToken:
    """
    A base class for all object that should be interpreted as validators
    """
    pass


T = TypeVar('T')


class GlobalValidationToken(ValidationToken, ABC):
    """
    A base class for all validators that can act on multiple kinds of fillers
    """

    @abstractmethod
    def __call__(self, stored_type: Type[T], filler) -> Callable[[Any], T]:
        """
        :param stored_type: the type the callback should return
        :param filler: the filler the validation callback will be called from
        :return: a callable to act as a validation callback for the specified filler
        """
        pass


class AssertValidation(GlobalValidationToken, ABC):
    """
    A validation token to check that a condition is upheld
    """

    def __init__(self, *, err: Union[str, Exception] = 'validation failed', warn: Union[bool, Logger] = False):
        """
        :param err: the error or warning to raise if the condition is not upheld.
        :param warn: whether to issue a warning instead if raising an error. Can also be an instance of a `Logger`,
         to specify the logger to warn with.
        """
        self.err = err
        self.warn = warn

    def _exc(self) -> Union[Exception, Warning]:
        """
        :return: The error or warning to raise when a condition is not upheld.
        """
        if isinstance(self.err, Exception):
            return self.err
        if self.warn:
            return UserWarning(self.err)
        return ValueError(self.err)

    def _raise(self):
        """
        raise the error or issue a warning
        """
        exc = self._exc()
        if self.warn:
            if self.warn is True:
                warnings.warn(exc)
            else:
                self.warn.warning(exc)
        else:
            raise exc

    @abstractmethod
    def assert_(self, v) -> bool:
        """
        :param v: the value to check.
        :return: Whether the condition is upheld for `v`.
        """
        pass

    def inner(self, v):
        """
        :param v: the value to validate
        """
        if not self.assert_(v):
            self._raise()
        return v

    def __call__(self, *_):
        return self.inner


class AssertCallValidation(AssertValidation, Generic[T]):
    """
    An assertion validation token to call arbitrary functions
    """
    def __init__(self, func: Callable[[T], bool], **kwargs):
        """
        :param func: the assertion function
        :param kwargs: forwarded to `AssertValidation.__init__`
        """
        super().__init__(**kwargs)
        self.func = func

    def assert_(self, v) -> bool:
        return self.func(v)


class CallValidation(GlobalValidationToken, Generic[T]):
    """
    An validation token to call arbitrary functions
    """
    def __init__(self, func: Callable[..., T], *args, **kwargs):
        """
        :param func: The callable to use as the validation callback.
        :param args: Optional positional arguments to pass to ``func``, after the validation argument.
        :param kwargs: Optional keyword arguments to pass to ``func``.

        .. note::

            calling ``CallValidation`` with ``args`` or ``kwargs`` is akin to calling it with a
            :py:func:`functools.partial` as ``func``.

            >>> CallValidation(foo, a, b, c=d)
            >>> # is equivalent to
            >>> CallValidation(lambda v: foo(v, a, b, c=d))
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def inner(self, v):
        return self.func(v, *self.args, **self.kwargs)

    def __call__(self, *_):
        return self.inner
