from __future__ import annotations

from collections import ChainMap
from inspect import getattr_static
from typing import AbstractSet, ClassVar, Dict, Type, TypeVar, Optional, Mapping, Any
from warnings import warn

import records.extras as extras
from records.fillers.filler import TypeCheckStyle
from records.fillers.get_filler import get_filler
from records.select import SelectableConstructor
from records.utils.typing_compatible import get_args, get_origin, get_type_hints

UNKNOWN_NAME = object()
NO_DEFAULT = object()
NO_ARG = object()

try:
    from typing import Final
except ImportError:  # pragma: no cover
    Final = object()


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

    def __init__(self, *, filler, owner, name, default):
        self.filler = filler
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
    def from_type_hint(cls, th, *, owner, **kwargs) -> RecordField:
        if th is Final:
            raise TypeError('raw Final cannot be use inside records')
        origin = get_origin(th)
        if origin == ClassVar:
            raise SkipField
        if origin == Final:
            if not owner.is_frozen():
                raise TypeError('cannot declare Final field in non-frozen Record')
            return cls.from_type_hint(get_args(th)[0], owner=owner, **kwargs)
        filler = get_filler(th)
        return cls(filler=filler, owner=owner, **kwargs)


T = TypeVar('T')


# noinspection PyNestedDecorators
class RecordBase:
    __slots__ = '_hash',

    _fields: ClassVar[Dict[str, RecordField]]
    _required_keys: ClassVar[AbstractSet[str]]
    _optional_keys: ClassVar[AbstractSet[str]]
    _default_type_check_style: ClassVar[TypeCheckStyle]
    _frozen: ClassVar[bool]

    def __init_subclass__(cls, *, frozen: bool = False, default_type_check=TypeCheckStyle.hollow, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.__init__ is not RecordBase.__init__:  # pragma: no cover
            warn(f'in class {cls}: must not override __init__')

        cls._frozen = frozen
        cls._default_type_check_style = default_type_check
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

        cls.cls_post_init()

        for field in cls._fields.values():
            field.filler.bind(cls)

    @classmethod
    def cls_post_init(cls):
        pass

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
            field = cls._fields.get(k)
            if not field:
                raise TypeError(f'argument {k} invalid for type {cls.__qualname__}')
            values[k] = field.filler(v)

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
        self = self.post_new() or self
        return self

    def post_new(self: T) -> Optional[T]:
        pass

    def __init__(self, arg=NO_ARG, **kwargs):
        pass

    def __repr__(self, **kwargs):
        params_parts = []
        for name, value in self.as_dict(**kwargs).items():
            params_parts.append(f'{name}={value!r}')

        return type(self).__qualname__ + "(" + ", ".join(params_parts) + ")"

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        for name in self._fields:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    @classmethod
    def _as_dict(cls, obj, include_defaults=False, sort_keys=False):
        # class method to export attribute dict, even from objects that are not instances of the type
        def export(f: RecordField, v):
            return include_defaults or (v != f.default)

        field_values = ((f, getattr(obj, f.name)) for f in cls._fields.values())
        name_values = ((f.name, v) for (f, v) in field_values if export(f, v))
        if sort_keys:
            name_values = sorted(name_values)

        return dict(name_values)

    def as_dict(self, **kwargs):
        return self._as_dict(self, **kwargs)

    @classmethod
    def is_frozen(cls):
        return cls._frozen

    @classmethod
    def default_type_check_style(cls):
        return cls._default_type_check_style

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(tuple(self.as_dict().values()))
        return self._hash

    @SelectableConstructor
    @classmethod
    def from_mapping(cls, *maps: Mapping[str, Any], **kwargs: Any):
        return ChainMap(*maps, dict(**kwargs))

    @SelectableConstructor
    @classmethod
    def from_identity(cls, v, *maps: Mapping[str, Any], **kwargs):
        d = cls._as_dict(v)
        d.update(*maps, **kwargs)
        return d

    @from_identity.shortcut
    @classmethod
    def from_instance(cls, v, *maps: Mapping[str, Any], **kwargs):
        if cls.is_frozen() and not maps and not kwargs and isinstance(v, cls):
            return v
        return NotImplemented

    @SelectableConstructor
    @classmethod
    def from_json(cls, v, **kwargs):
        if hasattr(v, 'read'):
            return extras.json.load(v, **kwargs)
        else:
            return extras.json.loads(v, **kwargs)
