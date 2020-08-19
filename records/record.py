from __future__ import annotations

from collections import ChainMap
from copy import deepcopy
from inspect import getattr_static
from typing import AbstractSet, Any, Callable, ClassVar, Container, List, Mapping, Optional, TypeVar, Union
from warnings import warn

import records.extras as extras
from records.field import NO_DEFAULT, FieldDict, RecordField, SkipField
from records.fillers.filler import TypeCheckStyle
from records.select import Exporter, NoArgExporter, SelectableConstructor, SelectableShortcutConstructor
from records.tags import Tag
from records.utils.typing_compatible import get_type_hints

try:
    from typing import Final
except ImportError:  # pragma: no cover
    Final = object()

NO_ARG = object()


def parser(func):
    func.__parser__ = True
    return func


class UnaryFailure(TypeError):
    pass


T = TypeVar('T')


# noinspection PyNestedDecorators
class RecordBase:
    __slots__ = '_hash',

    _fields: ClassVar[FieldDict]
    _required_keys: ClassVar[AbstractSet[str]]
    _optional_keys: ClassVar[AbstractSet[str]]
    _default_type_check_style: ClassVar[TypeCheckStyle]
    _frozen: ClassVar[bool]
    _unary_parse: ClassVar[bool]
    _parsers: ClassVar[List[Callable]]

    def __init_subclass__(cls, *, frozen: bool = None, unary_parse: Optional[bool] = None,
                          default_type_check=TypeCheckStyle.hollow, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.__init__ is not RecordBase.__init__:  # pragma: no cover
            warn(f'in class {cls}: must not override __init__')

        cls._frozen = frozen
        cls._default_type_check_style = default_type_check
        cls._fields = FieldDict()
        # in bodyless classes, __annotations__ refers to parent
        own_annotations = cls.__dict__.get('__annotations__', {})
        for name, type_hint in get_type_hints(cls, localns={cls.__name__: cls, cls.__qualname__: cls}).items():
            if name not in own_annotations:
                # type hints also give things from super classes which we don't want
                continue
            try:
                field = RecordField.from_type_hint(type_hint,
                                                   owner=cls, name=name,
                                                   default=getattr_static(cls, name, NO_DEFAULT))
            except SkipField:
                pass
            else:
                cls._fields[name] = field
                setattr(cls, name, field)

        parents = [b for b in cls.__bases__ if issubclass(b, RecordBase) and b != RecordBase]
        for parent in parents:
            for k, field in parent._fields.items():
                if cls._fields.setdefault(k, field) is not field:
                    raise ValueError(f'cannot override inherited field {k}')

        if cls.is_frozen() \
                and any(b for b in cls.__bases__ if b.__init__ not in (RecordBase.__init__, object.__init__)):
            warn(f'class {cls} has parents that implement __init__, the initializer will not be called!')

        if not cls._fields:
            raise ValueError(f'class {cls.__name__} has no fields')

        cls._required_keys = {k for (k, f) in cls._fields.items() if not f.has_default}
        cls._optional_keys = {k for k in cls._fields if k not in cls._required_keys}
        if unary_parse is None:
            unary_parse = len(cls._required_keys) != 1
        cls._unary_parse = unary_parse
        if frozen:
            cls.__setattr__ = RecordBase.__setattr__
            cls.__hash__ = RecordBase.__hash__
        else:
            cls.__setattr__ = object.__setattr__
            cls.__hash__ = None

        cls.pre_bind()

        for field in cls._fields.values():
            field.filler.bind(cls)

        cls._parsers = []
        for name in dir(cls):
            v = getattr_static(cls, name)
            if getattr(v, '__parser__', False):
                cls._parsers.append(getattr(cls, name))

    @classmethod
    def pre_bind(cls):
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
        super().__init__()

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
    def _to_dict(cls, obj, include_defaults=False, sort=None,
                 blacklist_tags: Union[Container[Tag], Tag] = frozenset(),
                 whitelist_keys: Union[Container[str], str] = frozenset()):
        # class method to export attribute dict, even from objects that are not instances of the type
        if isinstance(blacklist_tags, Tag):
            blacklist_tags = frozenset([blacklist_tags])
        if isinstance(whitelist_keys, str):
            whitelist_keys = frozenset([whitelist_keys])

        def export(f: RecordField, v):
            if f.name in whitelist_keys:
                return True
            if f.tags & blacklist_tags:
                return False
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
        # note: if the class is non-frozen, this function will be overridden
        if self._hash is None:
            self._hash = hash(tuple(self.to_dict().values()))
        return self._hash

    def __setattr__(self, a, value):
        # note: if the class is non-frozen, this function will be overridden
        if a in RecordBase.__slots__:
            return super().__setattr__(a, value)
        raise TypeError(f'{type(self).__qualname__} is frozen')

    def __getnewargs_ex__(self):
        return (), self.to_dict()

    @parser
    @SelectableConstructor
    @classmethod
    def from_mapping(cls, *maps: Mapping[str, Any], **kwargs: Any):
        return ChainMap(*maps, dict(**kwargs))

    @SelectableShortcutConstructor
    @classmethod
    def from_instance(cls, v, *maps: Mapping[str, Any], **kwargs):
        d = cls._to_dict(v)
        d.update(*maps, **kwargs)
        return d

    @parser
    @from_instance.shortcut
    @classmethod
    def from_instance(cls, v, *maps: Mapping[str, Any], **kwargs):
        if cls.is_frozen() and not maps and not kwargs and isinstance(v, cls):
            return v
        return NotImplemented

    @parser
    @SelectableConstructor
    @classmethod
    def from_json(cls, v, **kwargs):
        return extras.json.loads(v, **kwargs)

    @SelectableConstructor
    @classmethod
    def from_json_io(cls, v, **kwargs):
        return extras.json.load(v, **kwargs)

    @parser
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
        successes = []
        for m in cls._parsers:
            try:
                r = m(v)
            except Exception:
                pass
            else:
                successes.append(r)
        if len(successes) == 0:
            raise UnaryFailure(f'cannot unarily construct {cls.__qualname__} from argument of type '
                               f'{type(v).__qualname__}')
        elif len(successes) > 1:
            raise TypeError(f'multiple unary constructors succeeded with argument of type {type(v).__qualname__}')

        return next(iter(successes))

    @NoArgExporter
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

    def __copy__(self):
        if self.is_frozen():
            return self
        return type(self).from_instance(self)

    def __deepcopy__(self, memo=None):
        memo = memo or {}
        d = self.to_dict()
        d = deepcopy(d, memo)
        return self.from_mapping(d)
