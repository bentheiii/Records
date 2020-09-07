from __future__ import annotations

from typing import ClassVar, Dict, Set, Union

from records.fillers import AssertCallValidation, CallCoercion, CallValidation
from records.fillers.filler import Filler
from records.fillers.get_filler import get_filler
from records.tags import Tag
from records.utils.decorators import decorator_kw_method
from records.utils.typing_compatible import get_args, get_origin, split_annotation

try:
    from typing import Final
except ImportError:
    Final = object()

NO_DEFAULT = object()
SKIP_FIELD = object()


class Factory:
    """
    A function wrapper to specify that a default value should be treated as a factory method
    """

    def __init__(self, func):
        self.func = func


class RecordField:
    """
    A singular field in a record, each field is owned by a single RecordBase subclass
    """

    def __init__(self, *, filler: Filler, owner, name: str, default):
        """
        :param filler: the filler instance to use when filling the field
        :param owner: the owning RecordBase subclass the field is bound to
        :param name: the name of the field
        :param default: the default of the field, wrapped in ``Factory`` for factory functions, or the singleton
             ``NO_DEFAULT`` if there is no default.
        """
        self.filler = filler
        self.name = name
        default, is_factory = self._apply_factory(default)

        self.default = default
        self.default_is_factory = is_factory
        self.owner: type = owner

        self.tags: Set[Tag] = set()

    def make_default(self):
        """
        get a default value of the field, either from the default or default factory

        :return: An instance default value for the field.

        .. warning:: It is an error to call this method on a field without a default
        """
        if self.default_is_factory:
            return self.default()
        return self.default

    @property
    def has_default(self):
        """
        :return: whether or not the field has a default set
        """
        return self.default is not NO_DEFAULT

    def is_default(self, v):
        """
        :param v: the value to compare
        :return: whether ``v`` is equal to the default value, if one exists
        .. note::
            currently, fields with a factory default always return ``False`` for this method, this is subject to change
        """
        return (not self.default_is_factory) and self.default == v

    @classmethod
    def _apply_factory(cls, default):
        if isinstance(default, Factory):
            return default.func, True
        return default, False

    @classmethod
    def from_type_hint(cls, th, *, owner, **kwargs) -> Union[RecordField, type(SKIP_FIELD)]:
        """
        Create a field from a type hint.
        :param th: the type hint to use
        :param owner: the owner RecordBase subclass
        :param kwargs: all keyword arguments are forwarded to the ``RecordField.__init__``
        :return: a RecordField instance matching the type hint provided, or the sentinel ``SKIP_FIELD`` to indicate
         that this declaration should be skipped (in case of a ClassVar)
        """
        if th is Final:
            raise TypeError('raw Final cannot be use inside records')
        origin, args = split_annotation(th)
        meta_org = get_origin(origin)
        if meta_org == ClassVar:
            return SKIP_FIELD
        if meta_org is Final:
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
        """
        add a ``CallValidation`` to the field's filler.
        :param func: the callable to wrap inside the ``CallValidation``
        :param kwargs: all kwargs are forwarded to ``CallValidation``
        :return: func, to use as a decorator
        .. warning:: *must* be used inside of the owner class's `pre_bind` class method.
        .. code-block:: python

            class A(RecordBase):
                x: Annotated[int, check]
                @classmethod
                def pre_bind(cls):
                    super().pre_bind()
                    @cls.x.add_validator
                    def validator0():
                        ...

                    @cls.x.add_validator(a=0)
                    def validator1(a):
                        ...
        """
        self.filler.apply(CallValidation(func, **kwargs))
        return func

    @decorator_kw_method
    def add_assert_validator(self, func, **kwargs):
        """
        add a ``AssertCallValidation`` to the field's filler.
        :param func: the callable to wrap inside the ``AssertCallValidation``
        :param kwargs: all kwargs are forwarded to ``AssertCallValidation``
        :return: func, to use as a decorator
        .. warning:: *must* be used inside of the owner class's `pre_bind` class method.
        .. code-block:: python

            class A(RecordBase):
                x: Annotated[int, check]
                @classmethod
                def pre_bind(cls):
                    super().pre_bind()
                    @cls.x.add_assert_validator
                    def validator0():
                        ...

                    @cls.x.add_assert_validator(warn=True)
                    def validator1():
                        ...
        """
        self.filler.apply(AssertCallValidation(func, **kwargs))
        return func

    @decorator_kw_method
    def add_coercer(self, func, **kwargs):
        """
        add a ``CallCoercion`` to the field's filler.
        :param func: the callable to wrap inside the ``CallCoercion``
        :param kwargs: all kwargs are forwarded to ``CallCoercion``
        :return: func, to use as a decorator
        .. warning:: *must* be used inside of the owner class's `pre_bind` class method.
        .. code-block:: python

            class A(RecordBase):
                x: Annotated[int, check]
                @classmethod
                def pre_bind(cls):
                    super().pre_bind()
                    @cls.x.add_coercer
                    def coercion0():
                        ...

                    @cls.x.add_coercer(a=15)
                    def coercion1(a):
                        ...
        """
        self.filler.apply(CallCoercion(func, **kwargs))
        return func

    def _apply(self, token):
        if isinstance(token, Tag):
            self.tags.add(token)


class FieldDict(Dict[str, RecordField]):
    """
    A mapping from names to fields
    """

    def filter_by_tag(self, tag: Tag):
        """
        Filter the fields in the mapping to only those that have a tag
        :param tag: the tag to include
        :return: a new ``FieldDict`` including only the fields that possess tag_
        """
        return FieldDict((k, f) for (k, f) in self.items() if (tag in f.tags))
