from __future__ import annotations

from collections import ChainMap
from copy import deepcopy
from inspect import getattr_static
from typing import AbstractSet, Any, Callable, ClassVar, Container, Dict, List, Mapping, Optional, TypeVar, Union, \
    NamedTuple
from warnings import warn

import records.extras as extras
from records.field import NO_DEFAULT, SKIP_FIELD, FieldDict, RecordField
from records.fillers.filler import TypeCheckStyle
from records.select import Exporter, NoArgExporter, SelectableFactory, SpecializedShortcutFactory, Select
from records.tags import Tag
from records.utils.typing_compatible import get_type_hints

try:
    from typing import Final
except ImportError:
    Final = object()

NO_ARG = object()

exclude_from_ordering = Tag(object())


def parser(func: Callable):
    """
    mark a callable as a parser for a record class and all its subclasses
    :param func: the function to mark
    :return: ``func``, to used as a decorator
    """
    func.__parser__ = True
    return func


class ParseFailure(TypeError):
    """
    The error raised when an attempt to parse an object has failed because no parsers succeeded
    """
    pass


T = TypeVar('T')
FORBIDDEN_CLASS_ATTRS = ('__init__', '__setattr__', '__hash__')


# noinspection PyNestedDecorators
class RecordBase:
    """
    A superclass to all record classes
    """
    __slots__ = '_hash',

    # a dict of fields, by name
    _fields: ClassVar[FieldDict]
    # a (immutable) set of field names that have no default value
    _required_keys: ClassVar[AbstractSet[str]]
    # a (immutable) set of field names that have a default value
    _optional_keys: ClassVar[AbstractSet[str]]
    # the default type check style that fillers can use if they have none defined
    _default_type_check_style: ClassVar[TypeCheckStyle]
    # whether the class is frozen
    _frozen: ClassVar[bool]
    # whether to allow unary parsing in constructor
    _unary_parse: ClassVar[bool]
    # a mutable list of parsers
    _parsers: ClassVar[List[Callable]]
    # whether the class is ordered
    _ordered: ClassVar[bool]

    def __init_subclass__(cls, *, frozen: bool = False, unary_parse: Optional[bool] = None, ordered=False,
                          default_type_check=TypeCheckStyle.hollow, **kwargs):
        """
        sets up the record subclass

        :param frozen: Whether the class should be considered immutable (and thus, hashable)

        :param unary_parse: Whether to enable unary parsing. By default is only disabled if the class has exactly one
         required field.

        :param default_type_check: The default type checking style of the class, all fields will use this style unless
         otherwise specified.
        """
        super().__init_subclass__(**kwargs)

        for attr in FORBIDDEN_CLASS_ATTRS:
            if attr in cls.__dict__:
                warn(f'in class {cls}: must not override {attr} (method will be overridden)')

        cls._frozen = frozen
        cls._ordered = ordered
        cls._default_type_check_style = default_type_check
        cls._fields = FieldDict()
        # in bodyless classes, __annotations__ refers to parent
        own_annotations = cls.__dict__.get('__annotations__', {})
        for name, type_hint in get_type_hints(cls, localns={cls.__name__: cls, cls.__qualname__: cls}).items():
            if name not in own_annotations:
                # type hints also give things from super classes which we don't want
                continue
            # initialize the field
            field = RecordField.from_type_hint(type_hint,
                                               owner=cls, name=name,
                                               default=getattr_static(cls, name, NO_DEFAULT))
            if field is SKIP_FIELD:
                continue
            cls._fields[name] = field
            setattr(cls, name, field)

        # initialize inherited fields separately
        parents = [b for b in cls.__bases__ if issubclass(b, RecordBase) and b != RecordBase]
        parent_fields = {}
        for parent in parents:
            field: RecordField
            for k, field in parent._fields.items():
                if k in cls._fields or k in parent_fields:
                    raise ValueError(f'cannot override inherited field {k}')
                parent_fields[k] = field
        if parent_fields:
            cls._fields = {**parent_fields, **cls._fields}

        if any(b for b in cls.__bases__ if b.__init__ not in (RecordBase.__init__, object.__init__)):
            warn(f'class {cls} has parents that implement __init__, the initializer will not be called!')

        if not cls._fields:
            raise ValueError(f'class {cls.__name__} has no fields')

        cls._required_keys = {k for (k, f) in cls._fields.items() if not f.has_default}
        cls._optional_keys = {k for k in cls._fields if k not in cls._required_keys}
        if unary_parse is None:
            # be default, unary parse is only enabled if that is the only way to treat a positional parameter
            unary_parse = len(cls._required_keys) != 1
        cls._unary_parse = unary_parse
        if frozen:
            cls.__setattr__ = RecordBase.__setattr__
            cls.__hash__ = RecordBase.__hash__
        else:
            cls.__setattr__ = object.__setattr__
            cls.__hash__ = None

        # all validator tokens go here
        cls.pre_bind()

        for field in cls._fields.values():
            if field.owner is not cls:
                continue
            field.filler.bind(cls)

        cls._parsers = []
        for name in dir(cls):
            v = getattr_static(cls, name)
            if getattr(v, '__parser__', False):
                cls._parsers.append(getattr(cls, name))

    @classmethod
    def pre_bind(cls):
        """
        A class method that gets called when the class is initialized, but before all the field fillers are bound to the
        class. Subclasses may override this method and add validators and coercers to fields.
        """
        pass

    def __new__(cls, arg=NO_ARG, **kwargs):
        """
        Create an instance of the class.

        :param arg:
            If there is exactly one required field in the class (called the trivial field), the single
            positional argument can be used to fill it. Alternatively, if ``unary_parse`` has been enabled, ``arg`` can be
            used (without keyword arguments) to parse the argument.

        :param kwargs: The mapping is used to fill the values of all fields in the record instance.

        .. note::
            If ``arg`` can be interpreted as both a parsing argument and as the trivial field. A ``TypeError`` is
            raised.
        """
        # parsing stores the parsing result, if any
        parsing = None
        if arg is not NO_ARG:
            # handle the positional
            if not kwargs and cls._unary_parse:
                try:
                    parsing = cls.parse(arg)
                except ParseFailure:
                    # if we failed parsing, and we have no trivial field, raise an error
                    if len(cls._required_keys) != 1:
                        raise

            if len(cls._required_keys) != 1:
                # no trivial field
                if parsing is not None:
                    return parsing
                raise TypeError(f'class {cls.__qualname__} accepts no positional arguments')

            # we have a trivial field
            arg_key = next(iter(cls._required_keys))
            if arg_key in kwargs:
                raise TypeError(f'duplicate {arg_key}')
            kwargs[arg_key] = arg

        values = {}
        # keep track of which field are missing
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
            # if filling failed, check if we have a parsing standing by
            if parsing is not None:
                return parsing
            raise

        if required:
            raise TypeError(f'missing required arguments: {tuple(required)}')
        for k in optional:
            values[k] = cls._fields[k].make_default()

        self = super().__new__(cls)
        # we set directly into __dict__ because the class may be frozen and setattr would fail us
        self.__dict__.update(values)
        if cls._frozen:
            self._hash = None

        try:
            self = self.post_new() or self
        except Exception:
            # post_new may perform validations and if it fails, we want to return the parsing
            if parsing:
                return parsing
            raise

        # if we have successfully create an instance with positional argument, but still managed parsing, the we fail
        # we keep this check till last but
        if parsing is not None:
            raise TypeError(f'positional argument of type {type(arg)} can be interpreted both as trivial argument '
                            'and as unary argument')
        return self

    def post_new(self: T) -> Optional[T]:
        """
        This method is called after an instance is created and all its fields filled. This method may throw an exception
        to signal an invalid configuration.

        :return:
            May return a new instance, in which case it will replace the instance created, or ``None`` to
            keep it as is.
        """
        pass

    def __init__(self, arg=NO_ARG, **kwargs):
        # this init method ensures no other init methods run
        pass

    def __repr__(self, **kwargs):
        params_parts = []
        for name, value in self.to_dict(**kwargs).items():
            params_parts.append(f'{name}={value!r}')

        return type(self).__qualname__ + "(" + ", ".join(params_parts) + ")"

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if type(self).is_frozen() and hash(self) != hash(other):
            return False
        for name in self._fields:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    class _MockField(NamedTuple):
        """
        A "virtual" field used when extracting data, to mimic an actual field
        """
        name: str

        tags = frozenset()
        has_default = False

    @classmethod
    def _to_dict(cls, obj, include_defaults=False, sort=None,
                 blacklist_tags: Union[Container[Tag], Tag] = frozenset(),
                 whitelist_keys: Union[Container[str], str] = frozenset(),
                 _rev_select: Select = Select.empty) -> Dict[str, Any]:
        """
        Create a dict representing the values of the class's fields for an arbitrary objects

        :param obj: the object to get attributes from

        :param include_defaults: whether to include keys that match the default value.

        :param sort: whether to sort the keys of the dictionary numerically. If falsish, the keys will not be sorted.
        If equal to -1, the items will be sorted in reverse lexicographic order. If callable, the items will be sorted
        according to ``sort`` as a key. Otherwise, the items will be sorted lexicographically.
        :param blacklist_tags: A ``Tag`` or set of ``Tag``s to ignore all fields with the ``Tag``.

        :param whitelist_keys: A field name or set of field names to include regardless of ``blacklist`` and
        ``include_defaults``.

        :param _rev_select: A private `Select`, intended to be applied over the result, the function will attempt to
        extract the appropriate keys to fit the select

        :return: A ``dict`` object with key names as specified by ``include_defaults``, ``sort``, ``blacklist_tags``,
        ``whitelist_keys``, and with values according to ``obj``'s attributes.

        :raises AttributeError: if ``obj`` lacks an attribute that has not been blacklisted
        """
        if isinstance(blacklist_tags, Tag):
            blacklist_tags = frozenset([blacklist_tags])
        if isinstance(whitelist_keys, str):
            whitelist_keys = frozenset([whitelist_keys])

        # to save as many attribute accesses as we can, we pre-filter any field we can filter without knowing
        # their value.

        def export_field(f: RecordField):
            # check if we can rule out a field without even knowing its value
            return f.name in whitelist_keys or not (f.tags & blacklist_tags)

        def export_value(f: RecordField, v):
            return f.name in whitelist_keys \
                   or include_defaults or not (f.has_default and f.is_default(v))

        missing_ok = cls._optional_keys
        extraction_dict = cls._fields

        if _rev_select:
            missing_ok = set(missing_ok)
            extraction_dict = dict(extraction_dict)
            for to_remove in _rev_select.keys_to_remove:
                if to_remove in cls._fields:
                    continue
                extraction_dict[to_remove] = cls._MockField(name=to_remove)
            for old, new in _rev_select.keys_to_rename:
                missing_ok.add(new)
                extraction_dict[old] = cls._MockField(name=old)
            for old, new in _rev_select.keys_to_maybe_rename:
                missing_ok.add(new)
                missing_ok.add(old)
                extraction_dict[old] = cls._MockField(name=old)
            for key, _ in _rev_select.keys_to_add:
                extraction_dict.pop(key, _)
        fields_to_extract = extraction_dict.values()

        def tuples():
            # inner function to lazily get the key-value tuples
            for field in fields_to_extract:
                if not export_field(field):
                    continue

                try:
                    v = getattr(obj, field.name)
                except AttributeError:
                    if field.name not in missing_ok:
                        # we allow skipping missing fields if they have a default
                        raise
                    if include_defaults and field.has_default:
                        # but if the field is missing, and we expect to find it anyway, then we yield its tuple even
                        # though it was not present
                        yield field.name, field.make_default()
                else:
                    if export_value(field, v):
                        yield field.name, v

        name_values = tuples()
        if sort:
            if sort == -1:
                name_values = sorted(name_values, reverse=True)
            elif callable(sort):
                name_values = sorted(name_values, key=lambda t: sort(t[0]))
            else:
                name_values = sorted(name_values)

        return dict(name_values)

    @classmethod
    def is_frozen(cls):
        """
        :return: Whether the class is frozen.
        """
        return cls._frozen

    @classmethod
    def default_type_check_style(cls):
        """
        :return: The default type checking style.
        """
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
    @SelectableFactory
    @classmethod
    def from_mapping(cls, *maps: Mapping[str, Any], **kwargs: Any):
        """
        Convert a mapping to a Record instance.

        :param maps: Mappings to combine into field values.

        :param kwargs: Additional field name in the instance.

        :return: An instance of ``cls`` with arguments as described by the input mappings.

        .. note::
            This class method supports `selection`_.
        .. note::
            This class method is a registered parser that will be attempted when calling ``cls.parse``.
        """
        return ChainMap(*maps, dict(**kwargs))

    @SpecializedShortcutFactory
    @classmethod
    def from_instance(cls, v, *maps: Mapping[str, Any], _select=Select.empty, **kwargs):
        """
        Convert an object to a Record instance by attributes.

        :param v: An object to get attributes from.

        :param maps: Mappings to combine into field values.

        :param _select: a private `Select` to be used when extracting object attributes.

        :param kwargs: Additional field name in the instance.

        :return: An instance of ``cls`` with arguments as described by the input namespace and mappings.

        .. note::
            This class method supports `selection`_.
        .. note::
            If the class is frozen, and there are no additional mappings or kwargs supplied, the method may
            return ``v``.
        .. note::
            This class method is a registered parser that will be attempted when calling ``cls.parse``.
        """
        d = cls._to_dict(v, _rev_select=_select)
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
    @SelectableFactory
    @classmethod
    def from_json(cls, v, **kwargs):
        """
        Convert a JSON mapping to a Record instance.

        :param v: An JSON dictionary string to get attributes from.

        :param kwargs: Additional field name in the instance.

        :return: An instance of ``cls`` with arguments as described by the JSON.

        .. note::
            This class method supports `selection`_.
        .. note::
            This class method is a registered parser that will be attempted when calling ``cls.parse``.
        """
        return extras.json.loads(v, **kwargs)

    @SelectableFactory
    @classmethod
    def from_json_io(cls, v, **kwargs):
        """
        Convert a JSON file to a Record instance.

        :param v: An JSON dictionary file string to get attributes from.

        :param kwargs: Additional field name in the instance.

        :return: An instance of ``cls`` with arguments as described by the JSON.

        .. note::
            This class method supports `selection`_.
        """
        return extras.json.load(v, **kwargs)

    @parser
    @classmethod
    def from_pickle(cls, v, *args, **kwargs):
        """
        Convert a pickled bytestring to a Record instance.

        :param v: A bytestring object.

        :param args: forwarded to ``pickle.loads``

        :param kwargs: forwarded to ``pickle.loads``

        :return: An unpickled instance of ``cls``.

        .. note::
            If the unpickling result succeeds but the result is nto an instance of ``cls``, then ``cls`` attempts to
            parse the resulting object.\

        .. note::
            This class method is a registered parser that will be attempted when calling ``cls.parse``.
        """
        ret = extras.pickle.loads(v, *args, **kwargs)
        if not isinstance(ret, cls):
            return cls.parse(ret)
        return ret

    @classmethod
    def from_pickle_io(cls, v, *args, **kwargs):
        """
        Convert a pickled file to a Record instance.

        :param v: A record bytestring object.

        :param args: forwarded to ``pickle.load``

        :param kwargs: forwarded to ``pickle.load``

        :return: An unpickled instance of ``cls``.

        .. note::
            If the unpickling result succeeds but the result is nto an instance of ``cls``, then ``cls`` attempts
            to parse the resulting object.
        """
        ret = extras.pickle.load(v, *args, **kwargs)
        if not isinstance(ret, cls):
            return cls.parse(ret)
        return ret

    @classmethod
    def parse(cls, v):
        """
        Attempt to run all registered parsers of ``cls`` to parse an object to a ``cls`` instance.

        :param v: the object to attempt to parse.

        :return: The result of the only parser to succeed (raises an exception in all other cases).

        :raise ParseFailure: If none of the registered parsers succeed.

        :raise TypeError: If more than one of the registered parsers succeed.
        """
        successes = []
        for m in cls._parsers:
            try:
                r = m(v)
            except Exception:
                pass
            else:
                successes.append(r)
        if len(successes) == 0:
            raise ParseFailure(f'cannot parse {cls.__qualname__} from argument of type {type(v).__qualname__}')
        elif len(successes) > 1:
            raise TypeError(f'multiple unary constructors succeeded with argument of type {type(v).__qualname__}')

        return next(iter(successes))

    @NoArgExporter
    @staticmethod
    def to_dict(v) -> Mapping[str, Any]:
        """
        export an instance to a dictionary.
        .. note::
            This class method supports `selection`_ and `exporting arguments`_.
        """
        return v

    @Exporter
    @staticmethod
    def to_json(v, *args, io=None, **kwargs) -> str:
        """
        export an instance to a JSON dictionary.

        :param args: forwarded to either ``json.dump`` or ``json.dumps``

        :param io: If not ``None``, dumps ``self`` into ``io``.

        :param kwargs: forwarded to either ``json.dump`` or ``json.dumps``

        :return: ``None`` if ``io`` is not ``None``, otherwise a JSON string representing ``self``

        .. note::
            This class method supports selection and exporting arguments.
        """
        if io is None:
            return extras.json.dumps(v, *args, **kwargs)
        extras.json.dump(v, io, *args, **kwargs)

    def to_pickle(self, *args, io=None, **kwargs) -> bytes:
        """
        export an instance to a pickled bytestring.

        :param args: forwarded to either ``pickle.dump`` or ``pickle.dumps``

        :param io: If not ``None``, dumps ``self`` into ``io``.

        :param kwargs: forwarded to either ``pickle.dump`` or ``pickle.dumps``

        :return: ``None`` if ``io`` is not ``None``, otherwise a pickle bytestring representing ``self``
        """
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

    def __ordering_key(self):
        f: RecordField
        ret = []
        for k, f in type(self)._fields.items():
            if exclude_from_ordering in f.tags:
                continue
            ret.append(getattr(self, k))
        return ret

    def check_comparable(self, other):
        if not type(self)._ordered:
            raise TypeError(f'cannot compare with non-ordered type {type(self).__qualname__}')

    def __lt__(self, other):
        self.check_comparable(other)
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.__ordering_key() < other.__ordering_key()

    def __le__(self, other):
        self.check_comparable(other)
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.__ordering_key() <= other.__ordering_key()

    def __gt__(self, other):
        self.check_comparable(other)
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.__ordering_key() > other.__ordering_key()

    def __ge__(self, other):
        self.check_comparable(other)
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.__ordering_key() >= other.__ordering_key()
