from records.field import Factory
from records.fillers.builtin_fillers.std_fillers import (LiteralEval, Eval, FromInteger, Loose, LooseUnpack,
                                                         LooseUnpackMap, Falsish, Whole)
from records.fillers.builtin_validators import Clamp, Cyclic, FullMatch, Truth, Within
from records.fillers.coercers import CallCoercion, ClassMethodCoercion, ComposeCoercer, MapCoercion
from records.fillers.filler import TypeCheckStyle
from records.fillers.validators import AssertCallValidation, AssertValidation, CallValidation, ValidationToken
from records.record import RecordBase, parser, exclude_from_ordering
from records.select import SelectableFactory
from records.tags import Tag
from records.utils.typing_compatible import Annotated

check = TypeCheckStyle.check
check_strict = TypeCheckStyle.check_strict
hollow = TypeCheckStyle.hollow

__all__ = [
    'RecordBase', 'Annotated', 'Factory', 'parser', 'exclude_from_ordering',

    'TypeCheckStyle', 'check', 'check_strict', 'hollow',

    'CallCoercion', 'MapCoercion', 'ComposeCoercer', 'ClassMethodCoercion',
    'ValidationToken', 'AssertValidation', 'CallValidation', 'AssertCallValidation',
    'Clamp', 'Within', 'FullMatch', 'Truth', 'Cyclic',

    'Tag',
    'SelectableFactory',

    'Eval', 'LiteralEval', 'Loose', 'LooseUnpack', 'LooseUnpackMap', 'Whole', 'FromInteger',
    'Falsish'
]

# TODO:
#  * fill on assign? post_init_on assign? invariant?!
#  * more examples
#  * typevars?
#  * ways to add validators to sub-parsers
#  * allow multiple validators to succeed in Unions if they produce the same value
#  * todo fill trace-back (Union[Annotated[int, Negative], Annotated[bool, Loose]])
