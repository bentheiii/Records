from __future__ import annotations

from typing import Set, Final, ClassVar, Dict

from records.tags import Tag
from records.fillers import CallValidation, AssertCallValidation, CallCoercion
from records.fillers.get_filler import get_filler
from records.utils.decorators import decorator_kw_method
from records.utils.typing_compatible import split_annotation, get_origin, get_args

UNKNOWN_NAME = object()
NO_DEFAULT = object()


class Factory:
    def __init__(self, func):
        self.func = func


class DefaultValue:
    def __init__(self, value):
        self.value = value


class SkipField(Exception):
    pass


class RecordField:
    AUTO_FACTORY_TYPES = (dict, list, set)

    def __init__(self, *, filler, owner, name, default):
        self.filler = filler
        self.name = name
        default, is_factory = self._apply_factory(default)

        self.default = default
        self.default_is_factory = is_factory
        self.owner: type = owner

        self.tags: Set[Tag] = set()

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
        origin, args = split_annotation(th)
        meta_org = get_origin(origin)
        if meta_org == ClassVar:
            raise SkipField
        if meta_org == Final:
            if not owner.is_frozen():
                raise TypeError('cannot declare Final field in non-frozen Record')
            ret = cls.from_type_hint(get_args(origin)[0], owner=owner, **kwargs)
        else:
            filler = get_filler(th)
            ret = cls(filler=filler, owner=owner, **kwargs)
        for arg in args:
            ret._apply(arg)
        return ret

    @decorator_kw_method
    def add_validator(self, func, **kwargs):
        self.filler.apply(CallValidation(func, **kwargs))
        return func

    @decorator_kw_method
    def add_assert_validator(self, func, **kwargs):
        self.filler.apply(AssertCallValidation(func, **kwargs))
        return func

    @decorator_kw_method
    def add_coercer(self, func, **kwargs):
        self.filler.apply(CallCoercion(func, **kwargs))
        return func

    def _apply(self, token):
        if isinstance(token, Tag):
            self.tags.add(token)


class FieldDict(Dict[str, RecordField]):
    def filter_by_tag(self, key):
        if isinstance(key, Tag):
            return FieldDict((k, f) for (k, f) in self.items() if (key in f.tags))
        raise TypeError
