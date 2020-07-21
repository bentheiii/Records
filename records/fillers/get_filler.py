from records.fillers.builtin_fillers import builtin_filler_map, builtin_filler_checkers
from records.fillers.filler import AnnotatedFiller
from records.utils.typing_compatible import is_annotation, get_origin, get_args


def get_filler(stored_type):
    if not is_annotation(stored_type):
        return AnnotatedFiller(stored_type, ())
    origin = get_origin(stored_type)
    args = get_args(stored_type)
    by_type = getattr(origin, '__filler__', None)
    if by_type:
        return by_type(origin, args)
    blt = builtin_filler_map.get(origin)
    if blt:
        return blt(origin, args)
    if isinstance(stored_type, type):
        blt_subtypes = [k for (k, v) in builtin_filler_map.items() if issubclass(stored_type, k)]
        if len(blt_subtypes) > 1:
            raise Exception(f'cannot get builtin validator of {stored_type} (subtype of {blt_subtypes})')
        elif len(blt_subtypes) == 1:
            return builtin_filler_map[blt_subtypes[0]](origin, args)
    for checker in builtin_filler_checkers:
        ret = checker(origin)
        if ret:
            return ret(origin, args)
    raise TypeError(f'cannot find filler for {stored_type}')
