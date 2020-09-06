from typing import Any, Callable, Dict, List, Type, Union

from records.fillers.builtin_fillers.recurse import GetFiller
from records.fillers.filler import AnnotatedFiller

builtin_filler_map: Dict[Any, Type[AnnotatedFiller]] = {}
"""
a mapping of origin types to builtin filler types. If an exact match is not found in the map,
 then the checkers below are called, if none of them match, the mapping is checked again for subclassing.
"""
builtin_filler_checkers: List[Callable[[Any], Union[None, GetFiller, Type[AnnotatedFiller]]]] = []
"""
A sequence of callbacks to check if a storage type can be fitted to a filler type. Each callback should return `None`
 if there is no match, a `Filler` subclass if there is a match, or an instance of `GetFiller` for redirections.
"""
