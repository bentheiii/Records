from __future__ import annotations

from collections import ChainMap
from inspect import getattr_static
from typing import AbstractSet, ClassVar, Dict, Type, TypeVar, Optional, Mapping, Any
from warnings import warn

import records.extras as extras
from records.fillers.filler import TypeCheckStyle
from records.fillers.get_filler import get_filler
from records.select import SelectableConstructor, Select, SelectableShortcutConstructor, Exporter, NoArgExported
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


class UnaryFailure(TypeError):
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

    @property
    def has_default(self):
        return self.default is not NO_DEFAULT

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
    _unary_parse: ClassVar[bool]

    def __init_subclass__(cls, *, frozen: bool = False, unary_parse: Optional[bool] = None,
                          default_type_check=TypeCheckStyle.hollow, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.__init__ is not RecordBase.__init__:  # pragma: no cover
            warn(f'in class {cls}: must not override __init__')

        cls._frozen = frozen
        cls._default_type_check_style = default_type_check
        cls._fields = {}
        for name, type_hint in get_type_hints(cls, localns={cls.__name__: cls, cls.__qualname__: cls}).items():
            try:
                field = RecordField.from_type_hint(type_hint,
                                                   owner=cls, name=name,
                                                   default=getattr_static(cls, name, NO_DEFAULT))
            except SkipField:
                pass
            else:
                cls._fields[name] = field
                setattr(cls, name, field)

        cls._required_keys = {k for (k, f) in cls._fields.items() if not f.has_default}
        cls._optional_keys = {k for k in cls._fields if k not in cls._required_keys}
        if unary_parse is None:
            unary_parse = len(cls._required_keys) != 1
        cls._unary_parse = unary_parse
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
        parsing = None
        if arg is not NO_ARG:
            if not kwargs and cls._unary_parse:
                try:
                    parsing = cls.parse(arg)
                except UnaryFailure:
                    if len(cls._required_keys) != 1:
                        raise

            if len(cls._required_keys) != 1:
                if parsing is not None:
                    return parsing
                raise TypeError(f'class {cls.__qualname__} accepts no positional arguments')

            arg_key = next(iter(cls._required_keys))
            if arg_key in kwargs:
                raise TypeError(f'duplicate {arg_key}')
            kwargs[arg_key] = arg

        values = {}
        required = set(cls._required_keys)
        optional = set(cls._optional_keys)
        try:
            for k, v in kwargs.items():
                required.discard(k)
                optional.discard(k)
                field = cls._fields.get(k)
                if not field:
                    raise TypeError(f'argument {k} invalid for type {cls.__qualname__}')
                values[k] = field.filler(v)
        except Exception:
            if parsing is not None:
                return parsing
            raise

        if required:
            raise TypeError(f'missing required arguments: {tuple(required)}')
        for k in optional:
            values[k] = cls._fields[k].make_default()

        if parsing is not None:
            raise TypeError(f'positional argument of type {type(arg)} can be interpreted both as trivial argument '
                            'and as unary argument')

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
        for name, value in self.to_dict(**kwargs).items():
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
    def _to_dict(cls, obj, include_defaults=False, sort=None):
        # class method to export attribute dict, even from objects that are not instances of the type
        def export(f: RecordField, v):
            return include_defaults or (v != f.make_default())

        def tuples():
            for field in cls._fields.values():
                try:
                    v = getattr(obj, field.name)
                except AttributeError:
                    if not field.has_default:
                        raise
                else:
                    if export(field, v):
                        yield field.name, v

        name_values = tuples()
        if sort:
            if sort is True:
                name_values = sorted(name_values)
            elif sort == -1:
                name_values = sorted(name_values, reverse=True)
            else:
                name_values = sorted(name_values, key=lambda t: sort(t[0]))

        return dict(name_values)

    @classmethod
    def is_frozen(cls):
        return cls._frozen

    @classmethod
    def default_type_check_style(cls):
        return cls._default_type_check_style

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(tuple(self.to_dict().values()))
        return self._hash

    def __getnewargs_ex__(self):
        return (), self.to_dict()

    @SelectableConstructor
    @classmethod
    def from_mapping(cls, *maps: Mapping[str, Any], **kwargs: Any):
        # we have to raise typerror if the argument is not a mapping because we want the constructor to fail early
        if any(not isinstance(m, Mapping) for m in maps):
            raise TypeError
        return ChainMap(*maps, dict(**kwargs))

    @SelectableShortcutConstructor
    @classmethod
    def from_instance(cls, v, *maps: Mapping[str, Any], **kwargs):
        d = cls._to_dict(v)
        d.update(*maps, **kwargs)
        return d

    @from_instance.shortcut
    @classmethod
    def from_instance(cls, v, *maps: Mapping[str, Any], **kwargs):
        if cls.is_frozen() and not maps and not kwargs and isinstance(v, cls):
            return v
        return NotImplemented

    @SelectableConstructor
    @classmethod
    def from_json(cls, v, **kwargs):
        return extras.json.loads(v, **kwargs)

    @SelectableConstructor
    @classmethod
    def from_json_io(cls, v, **kwargs):
        return extras.json.load(v, **kwargs)

    @classmethod
    def from_pickle(cls, v, *args, **kwargs):
        ret = extras.pickle.loads(v, *args, **kwargs)
        if not isinstance(ret, cls):
            return cls.parse(ret)
        return ret

    @classmethod
    def from_pickle_io(cls, v, *args, **kwargs):
        ret = extras.pickle.load(v, *args, **kwargs)
        if not isinstance(ret, cls):
            return cls.parse(ret)
        return ret

    @classmethod
    def parse(cls, v):
        meths = (cls.from_json, cls.from_instance, cls.from_mapping, cls.from_pickle)
        successes = []
        for m in meths:
            try:
                r = m(v)
            except Exception as e:
                pass
            else:
                successes.append(r)
        if len(successes) == 0:
            raise UnaryFailure(f'cannot unarily construct {cls.__qualname__} from argument of type '
                               f'{type(v).__qualname__}')
        elif len(successes) > 1:
            raise TypeError(f'multiple unary constructors succeeded with argument of type {type(v).__qualname__}')

        return next(iter(successes))

    @NoArgExported
    @staticmethod
    def to_dict(v) -> Mapping[str, Any]:
        return v

    @Exporter
    @staticmethod
    def to_json(v, *args, io=None, **kwargs) -> str:
        if io is None:
            return extras.json.dumps(v, *args, **kwargs)
        extras.json.dump(v, io, *args, **kwargs)

    def to_pickle(self, *args, io=None, **kwargs) -> bytes:
        if io is None:
            return extras.pickle.dumps(self, *args, **kwargs)
        extras.pickle.dump(self, io, *args, **kwargs)
