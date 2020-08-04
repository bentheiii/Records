from typing import Any, Callable, Dict, List, Optional, Type

from records.fillers.filler import AnnotatedFiller

builtin_filler_map: Dict[Any, Type[AnnotatedFiller]] = {}
builtin_filler_checkers: List[Callable[[Any], Optional[Type[AnnotatedFiller]]]] = []
