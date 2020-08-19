from __future__ import annotations

from abc import abstractmethod
from itertools import chain
from typing import Any, Callable, Generic, Iterable, Mapping, Optional, Tuple, Type, TypeVar, Union


class Select:
    empty: Select

    def __init__(self, *,
                 keys_to_add: Union[Iterable[Tuple[str, Any]], Mapping[str, Any]] = (),
                 keys_to_maybe_add: Union[Iterable[Tuple[str, Any]], Mapping[str, Any]] = (),
                 keys_to_remove: Union[Iterable[str], str] = (),
                 keys_to_maybe_remove: Union[Iterable[str], str] = (),
                 keys_to_rename: Union[Iterable[Tuple[str, str]], Mapping[str, str]] = (),
                 keys_to_maybe_rename: Union[Iterable[Tuple[str, str]], Mapping[str, str]] = (),
                 ):
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

    def __call__(self, mapping: Mapping):
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


class SelectableClassDescriptor(Generic[T]):
    @abstractmethod
    def from_map(self, cls, map: Mapping[str, Any]) -> T:
        pass

    @abstractmethod
    def make_map(self, cls, *args, **kwargs) -> Mapping[str, Any]:
        pass

    def run(self, cls, args, kwargs, select: Select):
        mapping = self.make_map(cls, *args, **kwargs)
        mapping = select(mapping)
        return self.from_map(cls, mapping)

    def __get__(self, instance, owner):
        return self.Bound(self, owner, Select.empty)

    class Bound:
        def __init__(self, descriptor: SelectableClassDescriptor, owner_cls: Type, select: Select):
            self.descriptor = descriptor
            self.owner_cls = owner_cls
            self.select_ = select

        def __call__(self, *args, **kwargs):
            return self.descriptor.run(self.owner_cls, args, kwargs, self.select_)

        def select(self, *selects: Select, **kwargs):
            return type(self)(self.descriptor, self.owner_cls, self.select_.merge(*selects, **kwargs))


class SelectableConstructor(SelectableClassDescriptor):
    def __init__(self, func):
        if isinstance(func, classmethod):
            func = func.__func__
        self.func = func

    def from_map(self, cls, map: Mapping[str, Any]):
        return cls(**map)

    def make_map(self, cls, *args, **kwargs) -> Mapping[str, Any]:
        return self.func(cls, *args, **kwargs)


class SelectableShortcutConstructor(SelectableConstructor):
    def __init__(self, func, shortcut: Optional[Callable] = None):
        super().__init__(func)
        if isinstance(shortcut, classmethod):
            shortcut = shortcut.__func__
        self._shortcut = shortcut

    def shortcut(self, sc):
        if self._shortcut:  # pragma: no cover
            raise ValueError('cannot set multiple shortcuts')
        return type(self)(self.func, sc)

    def run(self, cls, args, kwargs, select: Select):
        if not select and self._shortcut:
            ret = self._shortcut(cls, *args, **kwargs)
            if ret is not NotImplemented:
                return ret
        return super().run(cls, args, kwargs, select)


class SelectableExporter(Generic[T]):
    @abstractmethod
    def from_mapping(self, m: Mapping[str, Any], *args, **kwargs) -> T:
        pass

    def run(self, instance, args, kwargs, export_args, export_kwargs, select):
        mapping = instance._to_dict(instance, *export_args, **export_kwargs)
        mapping = select(mapping)
        return self.from_mapping(mapping, *args, **kwargs)

    def __get__(self, instance, owner):
        if instance is None:  # pragma: no cover
            return self
        return self.Bound(self, instance, (), {}, Select.empty)

    class Bound:
        def __init__(self, descriptor: SelectableExporter, owner, export_args, export_kwargs, select):
            self.descriptor = descriptor
            self.owner = owner
            self.export_args = export_args
            self.export_kwargs = export_kwargs
            self.select_ = select

        def __call__(self, *args, **kwargs):
            return self.descriptor.run(self.owner, args, kwargs, self.export_args, self.export_kwargs, self.select_)

        def select(self, *selects: Select, **kwargs):
            return type(self)(self.descriptor, self.owner, self.export_args, self.export_kwargs,
                              self.select_.merge(*selects, **kwargs))

        def export_with(self, *args, **kwargs):
            return type(self)(self.descriptor, self.owner, (*self.export_args, *args), {**self.export_kwargs, **kwargs},
                              self.select_)


class Exporter(SelectableExporter):
    def __init__(self, func: Callable):
        if isinstance(func, staticmethod):
            func = func.__func__
        self.func = func

    def from_mapping(self, m: Mapping[str, Any], *args, **kwargs) -> T:
        return self.func(m, *args, **kwargs)


class NoArgExporter(Exporter):
    class Bound(Exporter.Bound):
        def __call__(self, *args, **kwargs):
            return self.descriptor.run(self.owner, (), {}, (*self.export_args, *args), {**self.export_kwargs, **kwargs},
                                       self.select_)
