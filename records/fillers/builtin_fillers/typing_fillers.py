from __future__ import annotations

import collections.abc as abstract_collections
import contextlib
from collections import defaultdict, deque
from collections.abc import Callable as CallableBase
from itertools import chain, islice
from typing import Any, Sequence, TypeVar, Union

from records.fillers.builtin_fillers.recurse import GetFiller
from records.fillers.filler import (AnnotatedFiller, Filler, TypeMatch, FillingSuccess, TypePassKind)
from records.fillers.get_filler import get_annotated_filler, get_filler
from records.utils.typing_compatible import get_args, get_origin

try:
    from typing import Literal
except ImportError:
    Literal = object()


class UnionFiller(Filler):
    """
    A filler for union types.
    """

    def __init__(self, origin, args):
        super().__init__()
        self.args = args
        self.sub_types = get_args(origin)
        self.sub_fillers: Sequence[Filler] = tuple(get_filler(a) for a in self.sub_types)
        self.applied = []

    def apply(self, token):
        super().apply(token)
        self.applied.append(token)

    def fill(self, arg):
        """
        The filling process for a Union is quite straight forward:
        * All of the union's inner arguments are parsed as fillers ion their own right, and are given the argument to
         type check
            * If any of these fillers succeed in exact type matching, only they are forwarded to the next stage.
            * Otherwise, if any of these fillers succeed in inexact type matching, only they are forwarded to the next
             stage.
            * Otherwise, if any of these fillers succeed in coercion, only they are forwarded to the next stage.
            * If no type checking succeed, the filling fails.
        * Then, all the successful sub-fillers are put through validation.
        * Validation succeeds only if exactly one sub-filler succeeded.
        """
        if self.is_hollow():
            return FillingSuccess(arg, TypePassKind.hollow)
        best_results = []
        best_key = float('inf')
        for i, sub_filler in enumerate(self.sub_fillers):
            try:
                success = sub_filler.fill(arg)
            except Exception:
                if not best_results and i + 1 == len(self.sub_fillers):
                    raise
                continue
            if success.type_pass_kind < best_key:
                best_results = [success.value]
                best_key = success.type_pass_kind
            elif success.type_pass_kind == best_key:
                best_results.append(success.value)

        if len(best_results) > 1 and any(r is not best_results[0] for r in best_results[1:]):
            raise ValueError('multiple sub-fillers matched')

        return FillingSuccess(best_results[0], best_key)

    def bind(self, owner_cls):
        super().bind(owner_cls)
        for sf in self.sub_fillers:
            for t in chain(self.args, self.applied):
                sf.apply(t)

            sf.bind(owner_cls)

    def is_hollow(self) -> bool:
        return all(sf.is_hollow() for sf in self.sub_fillers)

    def sub_filler(self, key):
        if isinstance(key, int):
            return self.sub_fillers[key]
        return super().sub_filler(key)


class LiteralFiller(AnnotatedFiller):
    """
    A filler for literal types.
    """

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
    """
    A convenience class for fillers to wrap other fillers, with additional functionality (usually adding validators)
    """

    def __init__(self, origin, args):
        super().__init__()
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
    """
    A filler for a parameterized typing.Type
    """

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
    """
    A filler for a parameterized typing.Tuple
    """

    def __init__(self, origin, args):
        super().__init__(get_origin(origin), args)
        self.inner_args = get_args(origin)
        if len(self.inner_args) == 2 and self.inner_args[-1] is ...:
            self.sub_fillers = (get_filler(self.inner_args[0]),)
        else:
            self.sub_fillers = tuple(get_filler(t) for t in self.inner_args)

    def bind(self, owner_cls):
        super().bind(owner_cls)

        if len(self.inner_args) == 2 and self.inner_args[-1] is ...:
            inner_filler = self.sub_fillers[0]
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
                    if len(v) != len(self.sub_fillers):
                        raise ValueError(f'must be a {len(self.sub_fillers)}-tuple')
                    return v

            for f in self.sub_fillers:
                f.bind(owner_cls)
            if not all(inner_filler.is_hollow() for inner_filler in self.sub_fillers):
                if self.is_hollow():
                    raise TypeError('cannot use non-hollow inner fillers in a hollow filler')

                @self.inner_filler.validators.append
                def _(v):
                    hollow_passes = 0  # the number of elements that filled identically
                    for element, filler in zip(v, self.sub_fillers):
                        filled = filler(element)
                        if filled is element:
                            hollow_passes += 1
                        else:
                            all_elements = chain(
                                v[:hollow_passes],
                                [filled],
                                (if_(a) for (a, if_) in zip(v[hollow_passes + 1:],
                                                            self.sub_fillers[hollow_passes + 1:]))
                            )
                            return type(v)(all_elements)
                    return v

    def sub_filler(self, key):
        if isinstance(key, int):
            return self.sub_fillers[key]
        return super().sub_filler(key)


def _split_at(seq, ignore_ind):
    """
    A utility function to split it in index, ignoring the element at the selected index
    :param seq: the sequence or iterable to split
    :param ignore_ind: the index to ignore
    :return: two iterables, one for `seq`'s elements up to `ignore_ind`, the second for all elements after.
    .. note::
        When used, the first iterable must be consumed entirely prior to the second one being consumed at all.
    """
    try:
        return seq[:ignore_ind], seq[ignore_ind + 1:]
    except TypeError:
        i = iter(seq)
        return islice(i, ignore_ind), islice(i, 1, None)


class GenericIterableFiller(WrapperFiller):
    """
    A filler for generic variants of concrete iterable classes.
    """

    def __init__(self, origin, args):
        super().__init__(get_origin(origin), args)
        self.inner_type = get_args(origin)[0]
        self.element_filler = get_filler(self.inner_type)

    def reconstruct(self, elements, initial):
        """
        reconstruct a filled instance that passed type checking, after its elements have mutated
        :param elements: the new elements of the iterable
        :param initial: The original filled argument. Must not be mutated.
        :return: A new instance of `initial`'s type, with `elements` as its elements.
        """
        return type(initial)(elements)

    def bind(self, owner_cls):
        super().bind(owner_cls)

        self.element_filler.bind(owner_cls)
        if not self.element_filler.is_hollow():
            if self.is_hollow():
                raise TypeError('cannot use non-hollow inner fillers in a hollow filler')

            @self.inner_filler.validators.append
            def inner_validator(v):
                hollow_passes = 0  # the number of elements that filled identically
                for element in v:
                    filled = self.element_filler(element)
                    if filled is element:
                        hollow_passes += 1
                    else:
                        pre, post = _split_at(v, hollow_passes)
                        all_elements = chain(
                            pre,
                            [filled],
                            (self.element_filler(a) for a in post)
                        )
                        return self.reconstruct(all_elements, v)
                return v

    def sub_filler(self, key):
        if key == 0:
            return self.element_filler
        return super().sub_filler(key)


class GenericDequeFiller(GenericIterableFiller):
    """
    A filler for generic deques
    """

    def reconstruct(self, elements, initial: deque):
        return type(initial)(elements, initial.maxlen)


class GenericMappingFiller(WrapperFiller):
    """
    A filler for generic variants of concrete mappings
    """

    def __init__(self, origin, args):
        super().__init__(get_origin(origin), args)
        self.key_type, self.value_type = get_args(origin)
        self.key_filler = get_filler(self.key_type)
        self.value_filler = get_filler(self.value_type)

    def reconstruct(self, tuples, initial):
        """
        reconstruct a filled instance that passed type checking, after its elements have mutated
        :param tuples: the new key-value tuples of the mapping
        :param initial: The original filled argument. Must not be mutated.
        :return: A new instance of `initial`'s type, with `tuples` as its tuples.
        """
        return type(initial)(tuples)

    def bind(self, owner_cls):
        super().bind(owner_cls)
        self.key_filler.bind(owner_cls)
        self.value_filler.bind(owner_cls)
        if not self.key_filler.is_hollow() or not self.value_filler.is_hollow():
            if self.is_hollow():
                raise TypeError('cannot use non-hollow inner fillers in a hollow filler')

            @self.inner_filler.validators.append
            def inner_validator(value):
                # there are no shortcuts here since maps can't be slices
                # (and thus this conversion would always require O(n) space)
                tuples = [
                    (self.key_filler(k), self.value_filler(v))
                    for k, v in value.items()
                ]
                if any(
                        (k is not filled_k) or (v is not filled_v)
                        for ((k, v), (filled_k, filled_v)) in zip(value.items(), tuples)
                ):
                    return self.reconstruct(tuples, value)
                else:
                    return value

    def sub_filler(self, key):
        if key == 0:
            return self.key_filler
        if key == 1:
            return self.value_filler
        return super().sub_filler(key)


class DefaultDictFiller(GenericMappingFiller):
    """
    A filler for generic defaultdicts
    """

    def reconstruct(self, tuples, initial):
        return type(initial)(initial.default_factory, tuples)


class GenericFillerN(WrapperFiller):
    """
    A filler for generic non-concrete classes or classes that otherwise can't have their parameters type-checked.
    """

    def __init__(self, origin, args):
        super().__init__(get_origin(origin), args)
        self.inner_types = get_args(origin)

    def bind(self, owner_cls):
        super().bind(owner_cls)

        fillers = [get_filler(it) for it in self.inner_types]
        for f in fillers:
            f.bind(owner_cls)
            if not f.is_hollow():
                raise TypeError('A non-specialized filler cannot have non-hollow inner types')


typing_checkers = []

genric_origin_map = {
    tuple: TupleFiller,
    type: TypeFiller,

    deque: GenericDequeFiller, defaultdict: DefaultDictFiller,

    abstract_collections.Sequence: GenericIterableFiller, abstract_collections.MutableSequence: GenericIterableFiller,
    abstract_collections.Set: GenericIterableFiller, abstract_collections.MutableSet: GenericIterableFiller,
    list: GenericIterableFiller, set: GenericIterableFiller, frozenset: GenericIterableFiller,

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
        return GetFiller(supertype)

    if stored_type is Any:
        return GetFiller(object)

    origin_cls = get_origin(stored_type)
    if origin_cls == Union:
        return UnionFiller
    if origin_cls == Literal:
        return LiteralFiller
    if origin_cls == type:
        if has_args(stored_type):
            return TypeFiller
        return GetFiller(type)
    if origin_cls == CallableBase:
        return GetFiller(callable)
    if has_args(stored_type):
        t = genric_origin_map.get(origin_cls)
        if t:
            return t
    elif origin_cls:
        return GetFiller(origin_cls)
