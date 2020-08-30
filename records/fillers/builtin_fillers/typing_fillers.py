from __future__ import annotations

import collections.abc as abstract_collections
import contextlib
from collections import defaultdict, deque
from collections.abc import Callable as CallableBase
from itertools import chain, islice
from typing import Any, List, Optional, Sequence, TypeVar, Union

from records.fillers.builtin_fillers.recurse import GetFiller
from records.fillers.filler import (AnnotatedFiller, Filler, TypeCheckingProcess, TypeCheckStyle, TypeMatch,
                                    TypePassKind, ValidationProcess)
from records.fillers.get_filler import get_annotated_filler, get_filler
from records.utils.typing_compatible import get_args, get_origin

no_eq = object()
try:
    from typing import Literal
except ImportError:  # pragma: no cover
    Literal = no_eq


class UnionTypeCheckingProcess(TypeCheckingProcess):
    def __init__(self, owner: UnionFiller, arg):
        self.owner = owner
        self.arg = arg

    def __call__(self):
        succeeded: Optional[List[ValidationProcess]] = None
        succeeded_kind: Optional[TypePassKind] = None
        for sf in self.owner.sub_fillers:
            try:
                validation: ValidationProcess = sf.fill(self.arg)()
            except Exception:
                continue
            if succeeded_kind is None or validation.type_pass < succeeded_kind:
                succeeded = [validation]
                succeeded_kind = validation.type_pass
            elif succeeded_kind == validation.type_pass:
                succeeded.append(validation)
        if not succeeded:
            raise TypeError('no type checkers succeeded')

        return UnionValidationProcess(self.owner, succeeded, succeeded_kind)


class UnionValidationProcess(ValidationProcess):
    def __init__(self, owner: UnionFiller, validations: List[ValidationProcess], type_pass: TypePassKind):
        self.owner = owner
        self.validations = validations
        self.type_pass = type_pass

    def __call__(self):
        good_results = []
        for validator_process in self.validations:
            try:
                result = validator_process()
            except Exception:
                continue
            good_results.append((result, validator_process))
        if not good_results:
            raise ValueError('no validators succeeded')
        elif len(good_results) > 1:
            raise ValueError(f'multiple validator success: {[gvt for (_, gvt) in good_results]}')
        return good_results[0][0]


class UnionFiller(AnnotatedFiller):
    def __init__(self, origin, args):
        super().__init__(origin, args)
        self.sub_types = get_args(origin)
        self.sub_fillers: Sequence[Filler] = ()
        self.applied = []

    def apply(self, token):
        super().apply(token)
        self.applied.append(token)

    def fill(self, arg):
        if self.type_checking_style == TypeCheckStyle.hollow:
            return super().fill(arg)
        return UnionTypeCheckingProcess(self, arg)

    def bind(self, owner_cls):
        super().bind(owner_cls)
        self.sub_fillers = [get_filler(a) for a in self.sub_types]
        for sf in self.sub_fillers:
            for t in chain(self.args, self.applied):
                sf.apply(t)

            sf.bind(owner_cls)
        if self.type_checking_style == TypeCheckStyle.hollow:
            if not all(sf.is_hollow() for sf in self.sub_fillers):
                self.type_checking_style = TypeCheckStyle.check
        else:
            if all(sf.is_hollow() for sf in self.sub_fillers):
                raise TypeError('non-hollow unions cannot be used with hollow inner types')

    type_check = type_check_strict = None


class LiteralFiller(AnnotatedFiller):
    def __init__(self, origin, args):
        super().__init__(origin, args)
        self.possible_values = defaultdict(set)
        for pv in get_args(origin):
            self.possible_values[type(pv)].add(pv)

    def type_check(self, v):
        if type(v) in self.possible_values:
            return TypeMatch.exact
        return isinstance(v, tuple(self.possible_values)) and TypeMatch.inexact

    def bind(self, owner_cls):
        super().bind(owner_cls)

        if not self.is_hollow():
            @self.validators.append
            def inner_validator(v):
                if v not in self.possible_values[type(v)]:
                    raise ValueError
                return v


class WrapperFiller(Filler):
    def __init__(self, origin, args):
        self.inner_filler = get_annotated_filler(origin, args)

    def fill(self, arg):
        return self.inner_filler.fill(arg)

    def bind(self, owner_cls):
        super().bind(owner_cls)
        self.inner_filler.bind(owner_cls)

    def is_hollow(self) -> bool:
        return self.inner_filler.is_hollow()

    def apply(self, token):
        self.inner_filler.apply(token)


class TypeFiller(WrapperFiller):
    def __init__(self, origin, args):
        super().__init__(get_origin(origin), args)
        self.base_type = get_args(origin)[0]

    def bind(self, owner_cls):
        super().bind(owner_cls)

        if not self.inner_filler.is_hollow():
            @self.inner_filler.validators.append
            def inner_validator(v):
                if not issubclass(v, self.base_type):
                    raise ValueError(f'must be a subclass of {self.base_type}')
                return v


class TupleFiller(WrapperFiller):
    def __init__(self, origin, args):
        super().__init__(get_origin(origin), args)
        self.inner_args = get_args(origin)

    def bind(self, owner_cls):
        super().bind(owner_cls)

        if len(self.inner_args) == 2 and self.inner_args[-1] is ...:
            inner_filler = get_filler(self.inner_args[0])
            inner_filler.bind(owner_cls)
            if not inner_filler.is_hollow():
                if self.is_hollow():
                    raise TypeError('cannot use non-hollow inner fillers in a hollow filler')

                @self.inner_filler.validators.append
                def inner_validator(v):
                    hollow_passes = 0  # the number of elements that filled identically
                    for element in v:
                        filled = inner_filler.__call__(element)
                        if filled is element:
                            hollow_passes += 1
                        else:
                            all_elements = chain(
                                v[:hollow_passes],
                                [filled],
                                (inner_filler.__call__(a) for a in v[hollow_passes + 1:])
                            )
                            return type(v)(all_elements)
                    return v
        else:
            if not self.is_hollow():
                @self.inner_filler.validators.append
                def _(v):
                    if len(v) != len(inner_fillers):
                        raise ValueError(f'must be a {len(inner_fillers)}-tuple')
                    return v

            inner_fillers = tuple(get_filler(t) for t in self.inner_args)
            for f in inner_fillers:
                f.bind(owner_cls)
            if not all(inner_filler.is_hollow() for inner_filler in inner_fillers):
                if self.is_hollow():
                    raise TypeError('cannot use non-hollow inner fillers in a hollow filler')

                @self.inner_filler.validators.append
                def _(v):
                    hollow_passes = 0  # the number of elements that filled identically
                    for element, filler in zip(v, inner_fillers):
                        filled = filler(element)
                        if filled is element:
                            hollow_passes += 1
                        else:
                            all_elements = chain(
                                v[:hollow_passes],
                                [filled],
                                (if_(a) for (a, if_) in zip(v[hollow_passes + 1:],
                                                            inner_fillers[hollow_passes + 1:]))
                            )
                            return type(v)(all_elements)
                    return v


def _split_at(seq, ignore_ind):
    try:
        return seq[:ignore_ind], seq[ignore_ind + 1:]
    except TypeError:
        i = iter(seq)
        return islice(i, ignore_ind), islice(i, 1, None)


class GenericIterableFiller1(WrapperFiller):
    def __init__(self, origin, args):
        super().__init__(get_origin(origin), args)
        self.inner_type = get_args(origin)[0]

    def reconstruct(self, elements, initial):
        return type(initial)(elements)

    def bind(self, owner_cls):
        super().bind(owner_cls)

        inner_filler = get_filler(self.inner_type)
        inner_filler.bind(owner_cls)
        if not inner_filler.is_hollow():
            if self.is_hollow():
                raise TypeError('cannot use non-hollow inner fillers in a hollow filler')

            @self.inner_filler.validators.append
            def inner_validator(v):
                hollow_passes = 0  # the number of elements that filled identically
                for element in v:
                    filled = inner_filler(element)
                    if filled is element:
                        hollow_passes += 1
                    else:
                        pre, post = _split_at(v, hollow_passes)
                        all_elements = chain(
                            pre,
                            [filled],
                            (inner_filler(a) for a in post)
                        )
                        return self.reconstruct(all_elements, v)
                return v


class GenericDequeFiller(GenericIterableFiller1):
    def reconstruct(self, elements, initial: deque):
        return type(initial)(elements, initial.maxlen)


class GenericMappingFiller(WrapperFiller):
    def __init__(self, origin, args):
        super().__init__(get_origin(origin), args)
        self.key_type, self.value_type = get_args(origin)

    def reconstruct(self, tuples, initial):
        return type(initial)(tuples)

    def bind(self, owner_cls):
        super().bind(owner_cls)

        key_filler = get_filler(self.key_type)
        value_filler = get_filler(self.value_type)
        key_filler.bind(owner_cls)
        value_filler.bind(owner_cls)
        if not key_filler.is_hollow() or not value_filler.is_hollow():
            if self.is_hollow():
                raise TypeError('cannot use non-hollow inner fillers in a hollow filler')

            @self.inner_filler.validators.append
            def inner_validator(value):
                # there are no shortcuts here since maps can't be slices
                # (and thus this conversion would always require O(n) space)
                tuples = [
                    (key_filler(k), value_filler(v))
                    for k, v in value.items()
                ]
                if any(
                        (k is not filled_k) or (v is not filled_v)
                        for ((k, v), (filled_k, filled_v)) in zip(value.items(), tuples)
                ):
                    return self.reconstruct(tuples, value)
                else:
                    return value


class DefaultDictFiller(GenericMappingFiller):
    def reconstruct(self, tuples, initial: defaultdict):
        return type(initial)(initial.default_factory, tuples)


class GenericFillerN(WrapperFiller):
    def __init__(self, origin, args):
        super().__init__(get_origin(origin), args)
        self.inner_types = get_args(origin)[0]

    def bind(self, owner_cls):
        super().bind(owner_cls)

        f = get_filler(self.inner_types)
        f.bind(owner_cls)
        if not f.is_hollow():
            raise TypeError('A non-specialized filler cannot have non-hollow inner types')


typing_checkers = []

genric_origin_map = {
    tuple: TupleFiller,
    type: TypeFiller,

    deque: GenericDequeFiller, defaultdict: DefaultDictFiller,

    abstract_collections.Sequence: GenericIterableFiller1, abstract_collections.MutableSequence: GenericIterableFiller1,
    abstract_collections.Set: GenericIterableFiller1, abstract_collections.MutableSet: GenericIterableFiller1,
    list: GenericIterableFiller1, set: GenericIterableFiller1, frozenset: GenericIterableFiller1,

    abstract_collections.Iterable: GenericFillerN, abstract_collections.Iterator: GenericFillerN,
    abstract_collections.Reversible: GenericFillerN, abstract_collections.Collection: GenericFillerN,
    abstract_collections.Container: GenericFillerN, abstract_collections.AsyncIterator: GenericFillerN,
    abstract_collections.AsyncIterable: GenericFillerN, contextlib.AbstractContextManager: GenericFillerN,
    contextlib.AbstractAsyncContextManager: GenericFillerN,

    abstract_collections.Mapping: GenericMappingFiller, abstract_collections.MutableMapping: GenericMappingFiller,
    dict: GenericMappingFiller,

    abstract_collections.AsyncGenerator: GenericFillerN, abstract_collections.Generator: GenericFillerN
}


def has_args(v):
    args = get_args(v)
    return args and any(not isinstance(a, TypeVar) for a in args)


@typing_checkers.append
def _typing(stored_type):
    supertype = getattr(stored_type, '__supertype__', None)  # handle newtype
    if supertype:
        raise GetFiller(supertype)

    if stored_type is Any:
        raise GetFiller(object)

    origin_cls = get_origin(stored_type)
    if origin_cls == Union:
        return UnionFiller
    if origin_cls == Literal:
        return LiteralFiller
    if origin_cls == type:
        if has_args(stored_type):
            return TypeFiller
        raise GetFiller(type)
    if origin_cls == CallableBase:
        raise GetFiller(callable)
    if has_args(stored_type):
        t = genric_origin_map.get(origin_cls)
        if t:
            return t
    elif origin_cls:
        raise GetFiller(origin_cls)
