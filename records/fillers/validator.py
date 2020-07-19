from abc import abstractmethod
from enum import IntEnum
from typing import TypeVar, Generic

from records.utils.typing_compatible import is_annotation, get_origin, get_args

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
     the value matches a use-specific constraint, and change it if it does not.
    A validation will only run if:
        a filler has not been aborted and has valdiators
    The outcome of validation:
        if a value is returned, a validation success is reported
        if an exception is raised, a validation error is reported
"""


def nil_validator(x):
    return x


T = TypeVar('T')


class TypeCheckFillingIntent(IntEnum):
    attempt_no_coerce = 0
    attempt_coerce = 1
    attempt_hollow = 2


class AnnotatedFiller(Generic[T]):
    def __init__(self, origin, args):
        self.origin = origin
        self.args = args
        self.coercers = []

    @abstractmethod
    def type_check_strict(self, v) -> bool:
        pass

    @abstractmethod
    def type_check(self, v) -> bool:
        pass

    def 


def get_validator(stored_type, extra_args=()):
    if not is_annotation(stored_type):
        return nil_validator
    origin = get_origin(stored_type)
    args = get_args(stored_type)
