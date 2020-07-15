import sys

from inspect import getattr_static
from operator import attrgetter
from typing import AbstractSet, Any, ClassVar, Dict, Literal, Union, get_type_hints

if sys.version_info >= (3, 8, 0):
    from typing import get_origin, get_args
else:
    get_origin = attrgetter('__origin__')
    get_args = attrgetter('__args__')  # todo callable needs special case

if sys.version_info >= (3, 9, 0):
    from typing import Annotated
else:
    Annotated = None

UNKNOWN_NAME = object()
NO_DEFAULT = object()
NO_ARG = object()


class SkipField(Exception):
    pass


class RecordField:
    def __init__(self, stored_type):
        self.stored_type = stored_type
        self.name = UNKNOWN_NAME
        self.default = NO_DEFAULT

    def set_default_value(self, v):
        if self.default is not NO_DEFAULT:  # pragma: no cover
            raise Exception('field already has a default')
        self.default = v

    def set_name(self, v):
        if self.name is not UNKNOWN_NAME:  # pragma: no cover
            raise Exception('field already has a name')
        self.name = v

    @classmethod
    def from_type_hint(cls, th):
        def multi(args):
            first, *tail = args
            ret = cls.from_type_hint(first)
            for t in tail:
                ret.apply(t)
            return ret

        if isinstance(th, type) or th in (Any,):
            return cls(th)
        origin = get_origin(th)
        if origin == ClassVar:
            raise SkipField
        if Annotated and origin == Annotated:
            return multi(get_args(th))
        if isinstance(origin, type) or origin in (Union, Literal):
            return cls(th)
        # todo Annotated, Any
        raise TypeError(type(th))


class RecordBase:
    __slots__ = '_hash',

    _fields: ClassVar[Dict[str, RecordField]]
    _required_keys: ClassVar[AbstractSet[str]]
    _frozen: ClassVar[bool]

    def __init_subclass__(cls, *, frozen: bool = False, **kwargs):
        super().__init_subclass__(**kwargs)

        cls._fields = {}
        for name, type_hint in get_type_hints(cls).items():
            try:
                field = RecordField.from_type_hint(type_hint)
            except SkipField:
                pass
            else:
                field.set_name(name)
                default = getattr_static(cls, name, NO_DEFAULT)
                if default is not NO_DEFAULT:
                    field.set_default_value(default)
                cls._fields[name] = field
                setattr(cls, name, field)

        cls._required_keys = {k for (k, f) in cls._fields.items() if f.default is NO_DEFAULT}
        cls._frozen = frozen
        if frozen:
            def __setattr__(s, a, value):
                if a in RecordBase.__slots__:
                    return super(cls, s).__setattr__(a, value)
                raise TypeError(f'{cls.__qualname__} is frozen')

            cls.__setattr__ = __setattr__
        else:
            cls.__hash__ = None

    def __new__(cls, arg=NO_ARG, **kwargs):
        if arg is not NO_ARG:
            if len(cls._required_keys) != 1:
                raise TypeError(f'non trivial class {cls.__qualname__} accepts no positional arguments')
            arg_key = next(iter(cls._required_keys))
            if arg_key in kwargs:
                raise TypeError(f'duplicate {arg_key}')
            kwargs[arg_key] = arg
        values = {name: field.default for (name, field) in cls._fields.items()}
        required = set(cls._required_keys)
        for k, v in kwargs.items():
            required.discard(k)
            if k not in values:
                raise TypeError(f'argument {k} invalid for type {cls.__qualname__}')
            values[k] = v

        if required:
            raise TypeError(f'missing required arguments: {tuple(required)}')

        self = super().__new__(cls)
        d = self.__dict__
        for k, v in values.items():
            d[k] = v
        if cls._frozen:
            self._hash = None
        return self

    def __init__(self, arg=NO_ARG, **kwargs):
        pass

    def __repr__(self, show_default=False):
        params_parts = []
        for name, field in self._fields.items():
            v = getattr(self, name)
            if not show_default and v is field.default:
                continue
            params_parts.append(f'{name}={v!r}')

        return type(self).__qualname__ + "(" + ", ".join(params_parts) + ")"

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        for name in self._fields:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def as_dict(self):
        return {
            name: getattr(self, name) for name in self._fields
        }

    @classmethod
    def is_frozen(cls):
        return cls._frozen

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(tuple(self.as_dict().values()))
        return self._hash
