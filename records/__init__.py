from records.field import Factory
from records.fillers.builtin_fillers.std_fillers import (Encoding, Eval, FromInteger, Loose, LooseUnpack,
                                                         LooseUnpackMap, SingletonFromFalsish, Whole)
from records.fillers.builtin_validators import Clamp, Cyclic, FullMatch, Truth, Within
from records.fillers.coercers import CallCoercion, ClassMethodCoercion, ComposeCoercer, MapCoercion
from records.fillers.filler import TypeCheckStyle
from records.fillers.validators import AssertCallValidation, AssertValidation, CallValidation, ValidationToken
from records.record import RecordBase, parser
from records.select import SelectableFactory
from records.tags import Tag
from records.utils.typing_compatible import Annotated

check = TypeCheckStyle.check
check_strict = TypeCheckStyle.check_strict
hollow = TypeCheckStyle.hollow

__all__ = [
    'RecordBase', 'Annotated', 'Factory', 'parser',

    'TypeCheckStyle', 'check', 'check_strict', 'hollow',

    'CallCoercion', 'MapCoercion', 'ComposeCoercer', 'ClassMethodCoercion',
    'ValidationToken', 'AssertValidation', 'CallValidation', 'AssertCallValidation',
    'Clamp', 'Within', 'FullMatch', 'Truth', 'Cyclic',

    'Tag',
    'SelectableFactory',

    'Eval', 'Loose', 'LooseUnpack', 'LooseUnpackMap', 'Whole', 'FromInteger',
    'SingletonFromFalsish', 'Encoding'
]

# TODO:
#  * documentation
#  * i'm pretty sure inheritance ruins the parent
#  * ensure add_validator and the like fail after binding
#  * fill on assign? post_init_on assign? invariant?!
#  * does selection work on from_instance?
#  * ordering
#  * add argument to Loose to only accept inputs of certain types
#  * typevars?
