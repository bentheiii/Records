from typing import NamedTuple, Any


class GetFiller(NamedTuple):
    """
    An object to be returned by a builtin filler factory to specify that a filler should be retrieved from the
    specified type
    """
    new_origin: Any
