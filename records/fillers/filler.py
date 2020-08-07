from abc import abstractmethod
from enum import Enum, IntEnum, auto
from typing import Any, Callable, Generator, Generic, List, Protocol, TypeVar, Iterable, Union, Type, Optional

from records.fillers.coercers import CoercionToken
from records.fillers.validators import ValidationToken

"""
Each field filling has multiple stages:
* Type checking (strict or non-strict)
    Makes sure the input is of the same type as the stored type. Strict checking only accepts values of the given type,
     and not sub-types. Strict type checking is illegal on abstract classes.
    Type checking will run only if:
        The type checking style has been set to Check, Check_strict, or Coerce
    The outcome of type checking:
        On success, report a no-coerce success to the parent
        On failure:
            * if the type checking style is Coerce, report a possible coerce match to the parent
            * if the type checking style does not allow coercion, report a failure to the parent
* coercion
    Attempts to coerce the value into the stored type. If the coercion function is run, it can be assumed that type
     checking has failed. The default coercers will perform the minimum amount of work possible. coercers SHOULD raise a
     TypeError if the value cannot be coerced. users can use custom coercers
    Coercion will run only if:
        The type checking style has been set to Coerce AND type checking has failed AND no other parallel filler has
        reported a no-coerce success
    The outcome of coercion:
        On success, report a coercion success
        On failure, report a failure
* validation
    After the type of the input has either been confirmed to be of the type, or coerced to the type, validators ensure
     the value matches a use-specific constraint, and change it or throw errors if it does not.
    A validation will only run if:
        a filler has not been aborted and has valdiators
    The outcome of validation:
        if a value is returned, a validation success is reported
        if an exception is raised, a validation error is reported
"""


class TypeCheckStyle(Enum):
    default = auto()
    hollow = auto()
    check = auto()
    check_strict = auto()


class FillingIntent(IntEnum):
    attempt_no_coerce_strict = 0
    attempt_no_coerce = 1
    attempt_coerce = 2
    attempt_hollow = 3

    attempt_validation = -1


class TypeMatch(Enum):
    exact = TypeCheckStyle.check_strict.value
    inexact = TypeCheckStyle.check.value


T = TypeVar('T')


class Filler(Protocol[T]):
    @abstractmethod
    def fill(self, arg) -> Generator[FillingIntent, None, T]:
        pass

    @abstractmethod
    def bind(self, owner_cls):
        pass

    @abstractmethod
    def is_hollow(self) -> bool:
        pass

    @abstractmethod
    def apply(self, token):
        if isinstance(token, Iterable):
            for t in token:
                self.apply(t)

    def __call__(self, arg):
        try:
            i = iter(self.fill(arg))
            while True:
                next(i)
        except StopIteration as si:
            return si.value


class AnnotatedFiller(Filler, Generic[T]):
    def __init__(self, origin, args):
        self.type_checking_style = TypeCheckStyle.default
        self.origin = origin
        self.args = args
        self.coercers: List[Callable[[Any], T]] = []
        self.validators: List[Callable[[T], T]] = []

    def fill(self, arg) -> Generator[FillingIntent, None, T]:
        if self.type_checking_style == TypeCheckStyle.default:  # pragma: no cover
            raise Exception

        if self.type_checking_style == TypeCheckStyle.hollow:
            yield FillingIntent.attempt_hollow
        else:
            tp = self.type_check(arg)
            if tp == TypeMatch.exact:
                yield FillingIntent.attempt_no_coerce_strict
            elif tp == TypeMatch.inexact and self.type_checking_style == TypeCheckStyle.check:
                yield FillingIntent.attempt_no_coerce
            else:
                # perform coercion
                yield FillingIntent.attempt_coerce
                if not self.coercers:
                    raise TypeError(f'failed type checking for value of type {type(arg)}')
                for i, coercer in enumerate(self.coercers):
                    try:
                        arg = coercer(arg)
                        tc = self.type_check(arg)
                        if tc is None \
                                or (tc == TypeMatch.inexact and self.type_checking_style != TypeCheckStyle.check):
                            raise TypeError(f'coercer returned value of wrong type: {type(arg)}')
                    except (TypeError, ValueError):
                        if i == len(self.coercers) - 1:
                            raise
                    else:
                        break

        # type checking done, perform validation
        yield FillingIntent.attempt_validation
        for validator in self.validators:
            arg = validator(arg)

        return arg

    def bind(self, owner_cls):
        for arg in self.args:
            self.apply(arg)
        if self.type_checking_style == TypeCheckStyle.default:
            self.type_checking_style = owner_cls.default_type_check_style()
        if self.type_checking_style == TypeCheckStyle.hollow and self.coercers:
            raise ValueError('cannot have hollow type checking with coercers')

    def apply(self, token):
        if isinstance(token, TypeCheckStyle):
            self.type_checking_style = token
        elif isinstance(token, CoercionToken) or (isinstance(token, type) and issubclass(token, CoercionToken)):
            self.coercers.append(self.get_coercer(token))
        elif isinstance(token, ValidationToken) or isinstance(token, type) and issubclass(token, ValidationToken):
            self.validators.append(self.get_validator(token))
        else:
            super().apply(token)

    @abstractmethod
    def type_check(self, v) -> Optional[TypeMatch]:
        pass

    def get_coercer(self, token: Union[CoercionToken, Type[CoercionToken]]) -> Callable[[Any], T]:
        if isinstance(token, type):
            return self.get_coercer(token())
        if callable(token):
            return token(self.origin, self)
        raise TypeError(token)  # pragma: no cover

    def get_validator(self, token: Union[ValidationToken, Type[ValidationToken]]) -> Callable[[T], T]:
        if isinstance(token, type):
            return self.get_coercer(token())
        if callable(token):
            return token
        raise TypeError(token)

    def is_hollow(self) -> bool:
        return self.type_checking_style == TypeCheckStyle.hollow
