from typing import Any, Dict, Type, List, Callable, Optional

from records.fillers.filler import AnnotatedFiller

from records.fillers.builtin_fillers.std_fillers import std_fillers
from records.fillers.builtin_fillers.std_fillers import Eval, Loose, LooseUnpack, LooseUnpackMap, Index, Whole, \
    FromBytes, FromInteger, FromFalsish, Encoding
from records.fillers.builtin_fillers.typing_fillers import typing_checkers

builtin_filler_map: Dict[Any, Type[AnnotatedFiller]] = {}
builtin_filler_checkers: List[Callable[[Any], Optional[Type[AnnotatedFiller]]]] = []

builtin_filler_map.update(std_fillers)
builtin_filler_checkers.extend(typing_checkers)

__all__ = ['builtin_filler_map', 'builtin_filler_checkers',

           'Eval', 'Loose', 'LooseUnpack', 'LooseUnpackMap', 'Index', 'Whole', 'FromBytes', 'FromInteger',
           'FromFalsish', 'Encoding']
