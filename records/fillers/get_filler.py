from records.fillers.builtin_fillers.recurse import GetFiller
from records.fillers.builtin_fillers.repo import builtin_filler_checkers, builtin_filler_map
from records.fillers.filler import Filler, TypeCheckStyle, TypePassKind
from records.utils.typing_compatible import get_args, get_origin, is_annotation


class DumbFiller(Filler):
    """
    A filler for objects that cannot be interpreted as types
    """

    def __init__(self, origin):
        super().__init__()
        self.origin = origin

    def fill(self, arg):
        def tc():
            return v

        def v():
            return arg

        v.type_pass = TypePassKind.hollow
        return tc

    def bind(self, owner_cls):
        super().bind(owner_cls)
        if owner_cls.default_type_check_style() is not TypeCheckStyle.hollow:
            raise TypeError(f'cannot have type checking for origin type {self.origin}')

    def apply(self, token):
        raise TypeError(f'cannot have tokens for origin type {self.origin}')

    def is_hollow(self) -> bool:
        return True


def get_filler(stored_type) -> Filler:
    """
    get a filler for a type hint
    :param stored_type: the type annotation to use as the storage type
    :return: the `Filler` to fill targeting `storage_type`
    """
    if not is_annotation(stored_type):
        return get_annotated_filler(stored_type, ())
    origin = get_origin(stored_type)
    args = get_args(stored_type)
    return get_annotated_filler(origin, args)


def get_annotated_filler(origin, args: tuple):
    """
    get a filler for a type hint with annotations.
    :param origin: the origin storage type.
    :param args: Annotated arguments for the filler.
    :return:
    .. note::
        usually it's preferable to call `get_filler` with `Annotated`.
    """
    # there are 4 ways a filler is made:
    blt = builtin_filler_map.get(origin)
    if blt:
        # a mapping of types to filler classes (for shourtcuts)
        return blt(origin, args)
    for checker in builtin_filler_checkers:
        # builtin functions to create a filler class
        ret = checker(origin)
        if isinstance(ret, GetFiller):
            return get_annotated_filler(ret.new_origin, args)
        elif ret:
            return ret(origin, args)
    if isinstance(origin, type):
        # run through all classes in the mapping checking for subtypes
        blt_supertype = next((k for (k, v) in builtin_filler_map.items() if issubclass(origin, k)), None)
        if blt_supertype:
            return builtin_filler_map[blt_supertype](origin, args)
    if args:
        raise TypeError(f'cannot have Annotated type with origin {origin}')
    # finally, return a dumb filler
    return DumbFiller(origin)
