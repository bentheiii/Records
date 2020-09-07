from __future__ import annotations

from abc import abstractmethod
from enum import Enum, IntEnum, auto
from typing import Any, Callable, Generic, List, Optional, TypeVar, NamedTuple

from records.fillers.coercers import CoercionToken
from records.fillers.util import _as_instance
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
    """
    Different ways to handle type-checking in fillers.
    """
    default = auto()
    """signifies that the filler should assume the type checking style of the owner record class upon binding.
     It is an error to have this style after binding"""
    hollow = auto()
    """signifies that no type checking or coercion should be performed"""
    check = auto()
    """signifies the filler should accept any argument of the type or its subclasses as valid arguments,
     and otherwise to fall back on coercion"""
    check_strict = auto()
    """signifies the filler should accept any argument of the exact type as valid arguments, and otherwise to fall
     back on coercion"""


class TypePassKind(IntEnum):
    """
    an inner enum to signify how a value passed a filler's type checking
    """
    no_coerce_strict = 0
    no_coerce = 1
    coerce = 2
    hollow = 3


T = TypeVar('T')


class FillingSuccess(NamedTuple):
    value: Any
    type_pass_kind: TypePassKind


class Filler(Generic[T]):
    """
    A base class for all fillers who must constrain arbitrary arguments to a (possibly annotated) storage type
    """

    def __init__(self):
        self.owner = None

    def sub_filler(self, key):
        """
        get a sub-filler of `self`
        :param key: the key to identify the filler by
        :return: the sub-filler of `self` corresponding to `key`
        :raises LookupError: if no sub-filler corresponding to `key` is found
        """
        if key is None:
            return self
        raise LookupError(f'filler {self} has no sub-filler of key {key}')

    @abstractmethod
    def fill(self, arg) -> FillingSuccess[T]:
        """
        Begin filling a value to match the filler's type checking and validation
        :param arg: the initial value to use
        :return: a ``FillingSuccess`` representing a successful filling process
        """
        pass

    @abstractmethod
    def bind(self, owner_cls):
        """
        Bind a filler and associate it with a class. After binding, no new tokens can be applied to the filler.
        :param owner_cls: the owner record class to associate the filler with.
        """
        if self.owner:
            raise RuntimeError(f'filler is already bound to {self.owner}')
        self.owner = owner_cls

    @abstractmethod
    def is_hollow(self) -> bool:
        """
        :return: Whether or not the filler is "hollow". A hollow filler is one that accepts input of any type.
        """
        pass

    @abstractmethod
    def apply(self, token):
        """
        Apply a token to a filler.
        :param token: The token provided to the filler through `Annotated`.
        """
        if self.owner:
            raise RuntimeError('cannot apply tokens to filler after binding')

    def __call__(self, arg) -> T:
        """
        Coerce and validate an argument by the filler
        :param arg: The argument to fill with
        :return: `arg` after coercion and validation.
        """
        tc = self.fill(arg)
        return tc.value


class TypeMatch(Enum):
    """
    How a value matches a target storage type
    """
    exact = auto()
    """
    An exact type match
    """
    inexact = auto()
    """
    An inexact type match
    """


class AnnotatedFiller(Filler, Generic[T]):
    """
    A simple parent class for many filler subclasses
    """

    def __init__(self, origin, args):
        """
        :param origin: The origin of the `Annotated` storage type
        :param args: The arguments of the `Annotated` storage type
        .. note::
            If the storage type is not an `Annotated`, `origin` should be the storage type and `args` should be an
            empty tuple.
        """
        super().__init__()
        self.type_checking_style = TypeCheckStyle.default
        self.origin = origin
        self.args = args
        self.coercers: List[Callable[[Any], T]] = []
        self.validators: List[Callable[[T], T]] = []

    def fill(self, arg):
        if self.type_checking_style == TypeCheckStyle.default:  # pragma: no cover
            raise Exception
        elif self.type_checking_style == TypeCheckStyle.hollow:
            tpk = TypePassKind.hollow
        else:
            tp = self.type_check(arg)
            if tp == TypeMatch.exact:
                tpk = TypePassKind.no_coerce_strict
            elif tp == TypeMatch.inexact and self.type_checking_style == TypeCheckStyle.check:
                tpk = TypePassKind.no_coerce
            else:
                # perform coercion
                if not self.coercers:
                    raise TypeError(f'failed type checking for value of type {type(arg)}')
                for i, coercer in enumerate(self.coercers):
                    try:
                        arg = coercer(arg)
                        tc = self.type_check(arg)
                        if tc is None \
                                or (tc == TypeMatch.inexact and self.type_checking_style != TypeCheckStyle.check):
                            raise TypeError(f'coercer returned value of wrong type: {type(arg)}')
                    except Exception:
                        if i == len(self.coercers) - 1:
                            raise
                    else:
                        break
                tpk = TypePassKind.coerce

        # validation
        for validator in self.validators:
            arg = validator(arg)

        return FillingSuccess(arg, tpk)

    def bind(self, owner_cls):
        for arg in self.args:
            self.apply(arg)
        super().bind(owner_cls)
        if self.type_checking_style == TypeCheckStyle.default:
            self.type_checking_style = owner_cls.default_type_check_style()
        if self.type_checking_style == TypeCheckStyle.hollow and self.coercers:
            raise ValueError('cannot have hollow type checking with coercers')

    def apply(self, token):
        super().apply(token)
        if isinstance(token, TypeCheckStyle):
            self.type_checking_style = token
            return
        coercion_token = _as_instance(token, CoercionToken)
        if coercion_token is not None:
            self.coercers.append(self.get_coercer(coercion_token))
            return
        validation_token = _as_instance(token, ValidationToken)
        if validation_token is not None:
            self.validators.append(self.get_validator(validation_token))
            return

    @abstractmethod
    def type_check(self, v) -> Optional[TypeMatch]:
        """
        Check whether a value matches the storage type
        :param v: the value to check
        :return: The `TypeMatch` kind in case of a match, or `None` if there is no type match.
        """
        pass

    def get_coercer(self, token: CoercionToken) -> Callable[[Any], T]:
        """
        Get a coercion callback from a coercion token.
        :param token: the token to get the callback from.
        :return: A coercion callback originating from the token.
        :raises TypeError: If the token cannot be interpreted for this filler.
        """
        if callable(token):
            return token(self.origin, self)
        raise TypeError(token)  # pragma: no cover

    def get_validator(self, token: ValidationToken) -> Callable[[T], T]:
        """
        Get a validation callback from a validation token.
        :param token: the token to get the callback from.
        :return: A validation callback originating from the token.
        :raises TypeError: If the token cannot be interpreted for this filler.
        """
        if callable(token):
            return token(self.origin, self)
        raise TypeError(token)  # pragma: no cover

    def is_hollow(self) -> bool:
        return self.type_checking_style == TypeCheckStyle.hollow
