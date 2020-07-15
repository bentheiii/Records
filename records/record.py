from inspect import getattr_static
from typing import get_type_hints, Any, get_origin, Union, Literal, Dict, Set, AbstractSet, ClassVar

UNKNOWN_NAME = object()
NO_DEFAULT = object()


class RecordField:
    def __init__(self, stored_type=Any, default=NO_DEFAULT):
        self.name = UNKNOWN_NAME
        self.stored_type = stored_type
        self.default = default

    def set_default_value(self, v):
        if self.default is not NO_DEFAULT:
            raise Exception('field already has a default')
        self.default = v

    def set_name(self, v):
        if self.name is not UNKNOWN_NAME:
            raise Exception('field already has a name')
        self.name = v

    @classmethod
    def from_type_hint(cls, th):
        if isinstance(th, cls):
            return th
        if isinstance(th, type) or th in (Any,):
            return cls(stored_type=th)
        origin = get_origin(th)
        if isinstance(origin, type) or origin in (Union, Literal):
            return cls(stored_type=th)
        # todo Annotated, Any
        raise TypeError(type(th))


class RecordBase:
    def __init_subclass__(cls, *, frozen: bool = False, **kwargs):
        super().__init_subclass__(**kwargs)

        cls._fields: Dict[str, RecordField] = {}
        for name, type_hint in get_type_hints(cls).items():
            try:
                field = RecordField.from_type_hint(type_hint)
            except TypeError:
                pass
            else:
                field.set_name(name)
                default = getattr_static(cls, name, NO_DEFAULT)
                if default is not NO_DEFAULT:
                    field.set_default_value(default)
                cls._fields[name] = field

        cls._required_keys: AbstractSet[str] = {k for (k, f) in cls._fields.items() if f.default is NO_DEFAULT}
        cls._frozen = frozen
        if not frozen:
            cls.__hash__ = None

    def __new__(cls, **kwargs):
        values = {name: field.default for (name, field) in cls._fields.items()}
        required = set(cls._required_keys)
        for k, v in kwargs.items():
            required.discard(k)
            values[k] = v

        if required:
            raise TypeError(f'missing required arguments: {tuple(required)}')

        self = super().__new__(cls)
        for k, v in values.items():
            setattr(self, k, v)
        if cls._frozen:
            self._hash = None
        return self

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

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(tuple(self.as_dict().values()))
        return self._hash
