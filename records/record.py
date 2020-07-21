from __future__ import annotations

from inspect import getattr_static
from typing import AbstractSet, Any, ClassVar, Dict, Literal, Type, Union

from records.utils.typing_compatible import (Annotated, get_origin,
                                             get_type_hints)

UNKNOWN_NAME = object()
NO_DEFAULT = object()
NO_ARG = object()


class ParamStorage:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class Check(ParamStorage):
    pass


class Coerce(ParamStorage):
    pass


class Pass:
    pass


class SkipField(Exception):
    pass


class Factory:
    def __init__(self, func):
        self.func = func


class DefaultValue:
    def __init__(self, value):
        self.value = value


class RecordField:
    AUTO_FACTORY_TYPES = (dict, list, set)

    def __init__(self, stored_type, *, owner, name, default):
        self.stored_type = stored_type
        self.name = name
        default, is_factory = self._apply_factory(default)

        self.default = default
        self.default_is_factory = is_factory
        self.owner: Type[RecordBase] = owner

    def make_default(self):
        if self.default_is_factory:
            return self.default()
        return self.default

    @classmethod
    def _apply_factory(cls, default):
        if isinstance(default, DefaultValue):
            return default.value, False
        if isinstance(default, Factory):
            return default.func, True
        if isinstance(default, cls.AUTO_FACTORY_TYPES):
            return default.copy, True
        return default, False

    @classmethod
    def from_type_hint(cls, th, **kwargs) -> RecordField:
        if isinstance(th, type) or th in (Any,):
            return cls(th, **kwargs)
        origin = get_origin(th)
        if origin == ClassVar:
            raise SkipField
        if isinstance(origin, type) or origin in (Union, Literal, Annotated):
            return cls(th, **kwargs)
        raise TypeError(type(th))


class RecordBase:
    __slots__ = '_hash',

    _fields: ClassVar[Dict[str, RecordField]]
    _required_keys: ClassVar[AbstractSet[str]]
    _optional_keys: ClassVar[AbstractSet[str]]
    _frozen: ClassVar[bool]

    def __init_subclass__(cls, *, frozen: bool = False, **kwargs):
        super().__init_subclass__(**kwargs)

        cls._frozen = frozen
        cls._fields = {}
        for name, type_hint in get_type_hints(cls).items():
            try:
                field = RecordField.from_type_hint(type_hint,
                                                   owner=cls, name=name,
                                                   default=getattr_static(cls, name, NO_DEFAULT))
            except SkipField:
                pass
            else:
                cls._fields[name] = field
                setattr(cls, name, field)

        cls._required_keys = {k for (k, f) in cls._fields.items() if f.default is NO_DEFAULT}
        cls._optional_keys = {k for k in cls._fields if k not in cls._required_keys}
        if frozen:
            def __setattr__(s, a, value):
                if a in RecordBase.__slots__:
                    return super(cls, s).__setattr__(a, value)
                raise TypeError(f'{cls.__qualname__} is frozen')

            cls.__setattr__ = __setattr__
        else:
            cls.__hash__ = None

        cls_post_init = getattr(cls, 'cls_post_init', None)
        if cls_post_init:
            cls_post_init()

    def __new__(cls, arg=NO_ARG, **kwargs):
        if arg is not NO_ARG:
            if len(cls._required_keys) != 1:
                raise TypeError(f'non trivial class {cls.__qualname__} accepts no positional arguments')
            arg_key = next(iter(cls._required_keys))
            if arg_key in kwargs:
                raise TypeError(f'duplicate {arg_key}')
            kwargs[arg_key] = arg

        values = {}
        required = set(cls._required_keys)
        optional = set(cls._optional_keys)
        for k, v in kwargs.items():
            required.discard(k)
            optional.discard(k)
            if k not in cls._fields:
                raise TypeError(f'argument {k} invalid for type {cls.__qualname__}')
            values[k] = v

        if required:
            raise TypeError(f'missing required arguments: {tuple(required)}')
        for k in optional:
            values[k] = cls._fields[k].make_default()

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
