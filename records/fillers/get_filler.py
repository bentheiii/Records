from records.fillers.builtin_fillers.recurse import GetFiller
from records.fillers.builtin_fillers.repo import builtin_filler_checkers, builtin_filler_map
from records.utils.typing_compatible import get_args, get_origin, is_annotation


def get_filler(stored_type):
    if not is_annotation(stored_type):
        return get_annotated_filler(stored_type, ())
    origin = get_origin(stored_type)
    args = get_args(stored_type)
    return get_annotated_filler(origin, args)


def get_annotated_filler(origin, args):
    by_type = getattr(origin, '__filler__', None)
    if by_type:
        return by_type(origin, args)
    for checker in builtin_filler_checkers:
        try:
            ret = checker(origin)
        except GetFiller as e:
            return get_annotated_filler(e.args[0], args)
        if ret:
            return ret(origin, args)
    blt = builtin_filler_map.get(origin)
    if blt:
        return blt(origin, args)
    if isinstance(origin, type):
        blt_supertype = next((k for (k, v) in builtin_filler_map.items() if issubclass(origin, k)), None)
        if blt_supertype:
            return builtin_filler_map[blt_supertype](origin, args)
    raise TypeError(f'cannot find filler for {origin}')