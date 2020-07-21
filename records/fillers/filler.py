from abc import abstractmethod
from enum import Enum, IntEnum, auto
from typing import Any, Callable, Generator, Generic, List, TypeVar, Protocol

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
    attempt_no_coerce = 0
    attempt_coerce = 1
    attempt_hollow = 2

    attempt_validation = -1


T = TypeVar('T')


class Filler(Protocol[T]):
    @abstractmethod
    def fill(self, arg) -> Generator[FillingIntent, None, T]:
        pass

    @abstractmethod
    def bind(self, owner_cls):
        pass


class AnnotatedFiller(Filler, Generic[T]):
    def __init__(self, origin, args):
        self.type_checking_style = TypeCheckStyle.default
        self.origin = origin
        self.args = args
        self.coercers: List[Callable[[Any], T]] = []
        self.validators: List[Callable[[T], T]] = []

    def fill(self, arg) -> Generator[FillingIntent, None, T]:
        if self.type_checking_style == TypeCheckStyle.default:
            raise NotImplementedError()

        if self.type_checking_style == TypeCheckStyle.hollow:
            yield FillingIntent.attempt_hollow
        else:
            yield FillingIntent.attempt_no_coerce
            if self.type_checking_style == TypeCheckStyle.check_strict:
                is_type = self.type_check_strict(arg)
            else:
                is_type = self.type_check(arg)

            if not is_type:
                # perform coercion
                yield FillingIntent.attempt_coerce
                if not self.coercers:
                    raise TypeError(f'failed type checking for value of type {type(arg)}')
                for i, coercer in enumerate(self.coercers):
                    try:
                        arg = coercer(arg)
                    except TypeError:
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
            raise NotImplementedError
        if self.type_checking_style == TypeCheckStyle.hollow and self.coercers:
            raise ValueError('cannot have hollow type checking with coercers')

    def apply(self, token):
        if isinstance(token, TypeCheckStyle):
            self.type_checking_style = token
        elif isinstance(token, CoercionToken):
            self.coercers.append(self.get_coercer(token))
        elif isinstance(token, ValidationToken):
            self.validators.append(self.get_validator(token))

    @abstractmethod
    def type_check_strict(self, v) -> bool:
        pass

    @abstractmethod
    def type_check(self, v) -> bool:
        pass

    def get_coercer(self, token: CoercionToken) -> Callable[[Any], T]:
        if callable(token):
            return token
        raise TypeError(token)

    def get_validator(self, token: ValidationToken) -> Callable[[T], T]:
        if callable(token):
            return token
        raise TypeError(token)
