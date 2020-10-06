from __future__ import annotations

from functools import update_wrapper
from itertools import chain
from typing import Any, Callable, Generic, Iterable, Mapping, Optional, Tuple, Type, TypeVar, Union


class Select:
    """
    A Select is a method of modifying a ``Mapping[str, Any]``. A Select should be considered immutable
    """
    empty: Select
    """An Empty Select, to be used as a default value to represent no mutations over a mapping"""

    def __init__(self, *,
                 keys_to_add: Union[Iterable[Tuple[str, Any]], Mapping[str, Any]] = (),
                 keys_to_maybe_add: Union[Iterable[Tuple[str, Any]], Mapping[str, Any]] = (),
                 keys_to_remove: Union[Iterable[str], str] = (),
                 keys_to_maybe_remove: Union[Iterable[str], str] = (),
                 keys_to_rename: Union[Iterable[Tuple[str, str]], Mapping[str, str]] = (),
                 keys_to_maybe_rename: Union[Iterable[Tuple[str, str]], Mapping[str, str]] = (),
                 ):
        """
        :param keys_to_add: Keys to add to the mapping, raising an error if they already exist
        :param keys_to_maybe_add: Keys to add to the mapping, or skip if they already exist
        :param keys_to_remove: Keys to remove from the mapping, raising an error if they don't exist. If a single
         string is presented, it is interpreted as a single key to remove.
        :param keys_to_maybe_remove: Keys to remove from the mapping if they exist. If a single string is presented,
         it is interpreted as a single key to remove.
        :param keys_to_rename: Keys to whose value to transfer to other keys inside the mapping, raising an error if the
         new name already exists
        :param keys_to_maybe_rename: Keys to whose value to transfer to other keys inside the mapping, or skip if the
         new name already exists
        """
        if isinstance(keys_to_add, Mapping):
            keys_to_add = tuple(keys_to_add.items())
        if isinstance(keys_to_maybe_add, Mapping):
            keys_to_maybe_add = tuple(keys_to_maybe_add.items())
        if isinstance(keys_to_rename, Mapping):
            keys_to_rename = tuple(keys_to_rename.items())
        if isinstance(keys_to_maybe_rename, Mapping):
            keys_to_maybe_rename = tuple(keys_to_maybe_rename.items())
        if isinstance(keys_to_remove, str):
            keys_to_remove = (keys_to_remove,)
        if isinstance(keys_to_maybe_remove, str):
            keys_to_maybe_remove = (keys_to_maybe_remove,)
        self.keys_to_add = keys_to_add
        self.keys_to_maybe_add = keys_to_maybe_add
        self.keys_to_remove = keys_to_remove
        self.keys_to_maybe_remove = keys_to_maybe_remove
        self.keys_to_rename = keys_to_rename
        self.keys_to_maybe_rename = keys_to_maybe_rename

        # the Select's truthiness is cached
        self._bool = None

    def _merge(self, other: Select):
        if not self:
            return other
        if not other:
            return self
        return type(self)(
            keys_to_add=tuple(chain(self.keys_to_add, other.keys_to_add)),
            keys_to_maybe_add=tuple(chain(self.keys_to_maybe_add, other.keys_to_maybe_add)),
            keys_to_remove=tuple(chain(self.keys_to_remove, other.keys_to_remove)),
            keys_to_maybe_remove=tuple(chain(self.keys_to_maybe_remove, other.keys_to_maybe_remove)),
            keys_to_rename=tuple(chain(self.keys_to_rename, other.keys_to_rename)),
            keys_to_maybe_rename=tuple(chain(self.keys_to_maybe_rename, other.keys_to_maybe_rename)),
        )

    def merge(self, *others: Select, **kwargs):
        """
        combine several Selects into one

        :param others: other selects to combine with ``self``

        :param kwargs: additional arguments to create a select with, and merge it.

        :return: a single :py:class:`Select`, formed by ``self``, all of ``others``, and a :py:class:`Select`
         formed with ``kwargs``
        """
        if not others and not kwargs:  # pragma: no cover
            raise TypeError('merge must be called with arguments')
        ret = self
        for other in others:
            ret = ret._merge(other)
        if kwargs:
            ret = ret._merge(type(self)(**kwargs))
        return ret

    def __bool__(self):
        if self._bool is None:
            self._bool = next(chain(
                self.keys_to_add,
                self.keys_to_maybe_add,
                self.keys_to_remove,
                self.keys_to_maybe_remove,
                self.keys_to_rename,
                self.keys_to_maybe_rename,
            ), None) is not None
        return self._bool

    def __call__(self, mapping: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        :param mapping: The mapping to use as input
        :return: A modified ``Mapping`` as specified by ``self``

        .. warning::
            This function may modify ``mapping``.
        """
        # this function may well alter the source mapping
        if not self:
            return mapping
        if not isinstance(mapping, dict):
            mapping = dict(mapping)

        for kti in self.keys_to_remove:
            mapping.pop(kti)
        for kti in self.keys_to_maybe_remove:
            mapping.pop(kti, None)
        for s, d in self.keys_to_rename:
            if d in mapping:
                raise ValueError(f'key {d} cannot be overridden in map')
            mapping[d] = mapping.pop(s)
        for s, d in self.keys_to_maybe_rename:
            if s not in mapping:
                continue
            if d in mapping:
                raise ValueError(f'key {d} cannot be overridden in map')
            mapping[d] = mapping.pop(s)
        for s, v in self.keys_to_add:
            if s in mapping:
                raise ValueError(f'key {s} cannot be overridden in map')
            mapping[s] = v
        for s, v in self.keys_to_maybe_add:
            if s in mapping:
                continue
            mapping[s] = v

        return mapping


Select.empty = Select()

T = TypeVar('T')


class SelectableFactory(Generic[T]):
    """
    A class to hold class factories that can be configured with the ``select`` method

    .. Note::
        Users can create their own SelectableFactory by using this class as decorator (on top of ``@classmethod``)
    """

    def __init__(self, func):
        """
        :param func: The function to wrap around, must return a mapping.
        """
        if isinstance(func, classmethod):
            func = func.__func__
        self.func: Callable[..., Mapping[str, Any]] = func
        update_wrapper(self, func)

    def run(self, cls: Type, args: Iterable, kwargs: Mapping[str, Any], select: Select):
        """
        run the factory with given arguments and selector
        :param cls: the owner class to create
        :param args: the arguments forwarded to ``func``
        :param kwargs: the keyword arguments forwarded to ``self.func``
        :param select: the select to apply on the mapping ``self.func`` returns
        :return: An instance of ``cls`` with arguments from ``self.func`` after ``select``.
        """
        mapping = self.func(cls, *args, **kwargs)
        mapping = select(mapping)
        return cls(**mapping)

    def __get__(self, instance, owner):
        """
        :return: The factory bound to an owner class
        """
        return self.Bound(self, owner, Select.empty)

    class Bound:
        """
        A bound instance of a ``SelectableFactory``
        """

        def __init__(self, descriptor: SelectableFactory, owner_cls: Type, select: Select):
            """
            :param descriptor: the ``SelectableFactory`` parent
            :param owner_cls: the owner class the instance is bound to
            :param select: the ``Select`` the instance should use
            """
            self.descriptor = descriptor
            self.owner_cls = owner_cls
            self.select_ = select
            update_wrapper(self, self.descriptor, updated=())

        def __call__(self, *args, **kwargs):
            return self.descriptor.run(self.owner_cls, args, kwargs, self.select_)

        def select(self, *selects: Select, **kwargs):
            """
            create a new bound factory with a modified :py:class:`.Select`

            :param selects: the new :py:class:`Selects <.Select>` to merge into the existing select

            :param kwargs: keyword argument to merge into the new :py:class:`Selects <.Select>`

            :return: a new bound factory
            """
            return type(self)(self.descriptor, self.owner_cls, self.select_.merge(*selects, **kwargs))


class SpecializedSelectableFactory(SelectableFactory):
    def run(self, cls: Type, args: Iterable, kwargs: Mapping[str, Any], select: Select):
        mapping = self.func(cls, *args, _select=select, **kwargs)
        mapping = select(mapping)
        return cls(**mapping)


class SelectableShortcutFactory(SelectableFactory):
    """
    A selectable factory with a shortcut function, that will be called if the ``select`` is false.
    """

    def __init__(self, func, shortcut: Optional[Callable] = None):
        super().__init__(func)
        if isinstance(shortcut, classmethod):
            shortcut = shortcut.__func__
        self._shortcut = shortcut

    def shortcut(self, sc):
        """
        Set a shortcut
        :param sc: the Shortcut function or class method. The shortcut function should either return an instance of the
         owner class or ``NotImplemented`` to indicate to fall back to main implementation.
        :return: a new ``SelectableShortcutFactory`` with ``sc`` as its shortcut.
        .. note::
            this function can be used as a decorator, provided that the shortcut function and main function have the
            same name.
        """
        if self._shortcut:  # pragma: no cover
            raise ValueError('cannot set multiple shortcuts')
        return type(self)(self.func, sc)

    def run(self, cls, args, kwargs, select: Select):
        if not select and self._shortcut:
            ret = self._shortcut(cls, *args, **kwargs)
            if ret is not NotImplemented:
                return ret
        return super().run(cls, args, kwargs, select)


class SpecializedShortcutFactory(SelectableShortcutFactory, SpecializedSelectableFactory):
    pass


class Exporter(Generic[T]):
    """
    An exported function that supports selection and additional exporting configuration

    .. Note::
        Users can create their own Exporter by using this class as decorator (on top of ``@staticmethod``)
    """

    def __init__(self, func: Callable):
        """
        :param func: the wrapped function, should accept the first positional argument a mapping.
        """
        if isinstance(func, staticmethod):
            func = func.__func__
        self.func = func
        self.owner: Optional[type] = None

        update_wrapper(self, func, updated=())

    def run(self, cls, instance, export_args, export_kwargs, select, args, kwargs):
        """
        runs the exporter
        :param instance: The instance to export
        :param export_args: the arguments of the exporting function `RecordBase._to_dict`_.
        :param export_kwargs: the keyword arguments of the exporting function `RecordBase._to_dict`_.
        :param select: the select to apply over the mapping before passing it to ``func``.
        :param args: the arguments of ``self.func``
        :param kwargs: the keyword arguments of ``self.func``
        :return: the result of ``func`` over the final mapping
        """
        mapping = cls._to_dict(instance, *export_args, **export_kwargs)
        mapping = select(mapping)
        return self.func(mapping, *args, **kwargs)

    def __get__(self, instance, owner):
        """
        Get a bound instance of an exporter function.
        """
        if instance is None:
            return self.BoundToClass(self, owner, (), {}, Select.empty)
        return self.Bound(self, instance, (), {}, Select.empty)

    class Bound:
        """
        An exporter bound to a specific instance
        """

        def __init__(self, descriptor: Exporter, owner, export_args, export_kwargs, select):
            """
            :param descriptor: The exporter

            :param owner: the owner instance that the object is bound to

            :param export_args: the arguments passed to `RecordBase._to_dict`_

            :param export_kwargs: the keyword arguments passed to `RecordBase._to_dict`_

            :param select: the select to apply
            """
            self.descriptor = descriptor
            self.owner = owner
            self.export_args = export_args
            self.export_kwargs = export_kwargs
            self.select_ = select
            update_wrapper(self, self.descriptor, updated=())

        def __call__(self, *args, **kwargs):
            return self.descriptor.run(self.owner, self.owner, self.export_args, self.export_kwargs, self.select_, args,
                                       kwargs)

        def select(self, *selects: Select, **kwargs):
            """
            create a new bound exporter with a modified :py:class:`.Select`

            :param selects: the new :py:class:`Selects <.Select>` to merge into the existing select

            :param kwargs: keyword argument to merge into the new :py:class:`.Select`

            :return: a new bound exporter
            """
            return type(self)(self.descriptor, self.owner, self.export_args, self.export_kwargs,
                              self.select_.merge(*selects, **kwargs))

        def export_with(self, *args, **kwargs):
            """
            create a new bound exporter with modified export arguments

            :param args: forwarded to :py:meth:`.RecordBase._to_dict`

            :param kwargs: forwarded to :py:meth:`.RecordBase._to_dict`

            :return: a new bound exporter
            """
            return type(self)(self.descriptor, self.owner, (*self.export_args, *args), {**self.export_kwargs, **kwargs},
                              self.select_)

    class BoundToClass(Bound):
        def __call__(self, instance, *args, **kwargs):
            return self.descriptor.run(self.owner, instance, self.export_args, self.export_kwargs, self.select_, args,
                                       kwargs)


class NoArgExporter(Exporter):
    """
    An exporter with the difference that ``func`` takes no arguments so all arguments are passed into
     `RecordBase._to_dict`_
    """

    def run(self, cls, instance, export_args, export_kwargs, select, args, kwargs):
        return super().run(cls, instance, (*export_args, *args), {**export_kwargs, **kwargs}, select, (), {})
