from records.field import DefaultValue, Factory
from records.fillers.builtin_fillers.std_fillers import (Encoding, Eval, FromInteger, Loose, LooseUnpack,
                                                         LooseUnpackMap, SingletonFromFalsish, Whole)
from records.fillers.builtin_validators import Clamp, Cyclic, FullMatch, Truth, Within
from records.fillers.coercers import CallCoercion, ClassMethodCoercion, ComposeCoercer, MapCoercion
from records.fillers.filler import TypeCheckStyle
from records.fillers.validators import AssertCallValidation, AssertValidation, CallValidation, ValidationToken
from records.record import RecordBase, parser
from records.select import SelectableConstructor
from records.tags import Tag
from records.utils.typing_compatible import Annotated

check = TypeCheckStyle.check
check_strict = TypeCheckStyle.check_strict
hollow = TypeCheckStyle.hollow

__all__ = [
    'RecordBase', 'Annotated', 'Factory', 'DefaultValue', 'parser',

    'TypeCheckStyle', 'check', 'check_strict', 'hollow',

    'CallCoercion', 'MapCoercion', 'ComposeCoercer', 'ClassMethodCoercion',
    'ValidationToken', 'AssertValidation', 'CallValidation', 'AssertCallValidation',
    'Clamp', 'Within', 'FullMatch', 'Truth', 'Cyclic',

    'Tag',
    'SelectableConstructor',

    'Eval', 'Loose', 'LooseUnpack', 'LooseUnpackMap', 'Whole', 'FromInteger',
    'SingletonFromFalsish', 'Encoding'
]

# TODO:
#  * fill on assign?
#  * ordering
#  * add argument to Loose to only accept inputs of certain types
#  * typevars?
