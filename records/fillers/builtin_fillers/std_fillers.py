from abc import abstractmethod
from functools import partial
from math import isclose
from numbers import Rational, Real
from operator import index
from typing import Generic, TypeVar, Callable, Type, Tuple, Dict, Any

from records.fillers.filler import AnnotatedFiller, CoercionToken

T = TypeVar('T')


class KwCoercionToken(CoercionToken, Generic[T]):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def get_base(self, origin: Type[T]) -> Callable[..., T]:
        pass


class Eval(KwCoercionToken[T], Generic[T]):
    def get_base(self, origin) -> Callable[..., T]:
        def ret(v):
            if not isinstance(v, str):
                raise TypeError
            try:
                ret = eval(v, {'__builtins__': {}})
            except Exception as e:
                raise TypeError from e

            if type(ret) is not origin:
                raise TypeError

            return ret

        return ret


class Loose(KwCoercionToken[T], Generic[T]):
    def get_base(self, origin) -> Callable[..., T]:
        return origin


class LooseUnpack(KwCoercionToken[T], Generic[T]):
    def get_base(self, origin: Type[T]) -> Callable[..., T]:
        def ret(v, *args, **kwargs):
            return origin(*v, *args, **kwargs)

        return ret


class LooseUnpackMap(KwCoercionToken[T], Generic[T]):
    def get_base(self, origin: Type[T]) -> Callable[..., T]:
        def ret(v, *args, **kwargs):
            return origin(**v, *args, **kwargs)

        return ret


class SimpleFiller(AnnotatedFiller[T], Generic[T]):
    PARTIAL_COERCER_TYPES: Tuple[Type[KwCoercionToken], ...] = Eval, Loose, LooseUnpack, LooseUnpackMap

    def type_check_strict(self, v) -> bool:
        return type(v) == self.origin

    def type_check(self, v) -> bool:
        return isinstance(v, self.origin)

    def get_coercer(self, token):
        if isinstance(token, self.PARTIAL_COERCER_TYPES):
            token: KwCoercionToken
            base = token.get_base(self.origin)
            if token.args or token.kwargs:
                return partial(base, *token.args, **token.kwargs)
            return base
        return super().get_coercer(token)


class Index(KwCoercionToken[int]):
    def get_base(self, origin) -> Callable[..., T]:
        return index


class Whole(KwCoercionToken[int]):
    def get_base(self, origin) -> Callable[..., T]:
        def ret(v, *args, **kwargs):
            if isinstance(v, Rational):
                if v.denominator == 1:
                    return origin(v, *args, **kwargs)
            elif isinstance(v, Real):
                mod = v % 1
                if isclose(mod, 0) or isclose(mod, 1):
                    return origin(v, *args, **kwargs)
            raise TypeError

        return ret


class FromBytes(KwCoercionToken[T], Generic[T]):
    def get_base(self, origin) -> Callable[..., T]:
        return origin.from_bytes


class IntFiller(SimpleFiller[int]):
    PARTIAL_COERCER_TYPES = *SimpleFiller.PARTIAL_COERCER_TYPES, Index, Whole, FromBytes


class FromInteger(SimpleFiller[T], Generic[T]):
    @staticmethod
    def _bool(v):
        if v == 0:
            return False
        if v == 1:
            return True
        raise TypeError

    def get_base(self, origin) -> Callable[..., T]:
        if issubclass(origin, bool):
            return self._bool
        if issubclass(origin, (bytes, bytearray)):
            def _bytes(v, *args, **kwargs):
                return origin(v.to_bytes(*args, **kwargs))

            return _bytes
        raise ValueError(origin)


class BoolFiller(SimpleFiller[bool]):
    PARTIAL_COERCER_TYPES = *SimpleFiller.PARTIAL_COERCER_TYPES, FromInteger


class FromFalsish(SimpleFiller[T], Generic[T]):
    def get_base(self, origin) -> Callable[..., T]:
        def ret(v, *args, **kwargs):
            if not v:
                return origin(*args, **kwargs)
            raise TypeError

        return ret


class NoneFiller(SimpleFiller[None]):
    def type_check(self, v) -> bool:
        return v is None

    type_check_strict = type_check

    PARTIAL_COERCER_TYPES = *SimpleFiller.PARTIAL_COERCER_TYPES, FromFalsish


class Encoding(Loose[T], Generic[T]):
    def __init__(self, encoding, **kwargs):
        super().__init__(encoding=encoding, **kwargs)


class StrFiller(SimpleFiller[str]):
    PARTIAL_COERCER_TYPES = *SimpleFiller.PARTIAL_COERCER_TYPES, Encoding


class BytesFiller(SimpleFiller[bytes]):
    PARTIAL_COERCER_TYPES = *SimpleFiller.PARTIAL_COERCER_TYPES, Encoding


class CallableFiller(AnnotatedFiller[Callable]):
    type_check = type_check_strict = callable


std_fillers: Dict[Any, Type[AnnotatedFiller]] = {
    int: IntFiller,
    bool: BoolFiller,
    str: StrFiller,
    bytes: BytesFiller,
    callable: CallableFiller,
    None: NoneFiller,
}
std_fillers[type(None)] = std_fillers[None]

for t in (complex, list, tuple, set, frozenset, range, slice, Exception, type, dict):
    std_fillers[t] = SimpleFiller
