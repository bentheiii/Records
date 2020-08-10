from records.fillers.builtin_fillers.std_fillers import (Encoding, Eval, FromBytes, SingletonFromFalsish, FromInteger,
                                                         Loose, LooseUnpack, LooseUnpackMap, Whole)
from records.fillers.filler import TypeCheckStyle
from records.record import DefaultValue, Factory, RecordBase
from records.utils.typing_compatible import Annotated
from records.fillers.coercers import CallCoercion, MapCoercion, ComposeCoercer
from records.fillers.builtin_validators import Clamp, Within, FullMatch, Truth, Cyclic
from records.fillers.validators import ValidationToken, AssertValidation, CallValidation, AssertCallValidation

check = TypeCheckStyle.check
check_strict = TypeCheckStyle.check_strict
hollow = TypeCheckStyle.hollow

__all__ = [
    'RecordBase', 'Annotated', 'Factory', 'DefaultValue',

    'TypeCheckStyle', 'check', 'check_strict', 'hollow',

    'CallCoercion', 'MapCoercion', 'ComposeCoercer',
    'ValidationToken', 'AssertValidation', 'CallValidation', 'AssertCallValidation',
    'Clamp', 'Within', 'FullMatch', 'Truth', 'Cyclic',

    'Eval', 'Loose', 'LooseUnpack', 'LooseUnpackMap', 'Whole', 'FromBytes', 'FromInteger',
    'SingletonFromFalsish', 'Encoding'
]

# TODO:
#  * idiomatic new
#  * json coercion
#  * exporting records
#  * field tags (for exporting)
#  * __copy__
#  * handle
