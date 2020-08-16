from records.fillers.builtin_fillers.std_fillers import (Encoding, Eval, SingletonFromFalsish, FromInteger, Loose,
                                                         LooseUnpack, LooseUnpackMap, Whole)
from records.fillers.filler import TypeCheckStyle
from records.record import DefaultValue, Factory, RecordBase, parser
from records.utils.typing_compatible import Annotated
from records.fillers.coercers import CallCoercion, MapCoercion, ComposeCoercer, ClassMethodCoercion
from records.fillers.builtin_validators import Clamp, Within, FullMatch, Truth, Cyclic
from records.fillers.validators import ValidationToken, AssertValidation, CallValidation, AssertCallValidation
from records.select import SelectableConstructor
from records.tags import Tag

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
#  * can we parse Enums with Eval?
#  * handle inheritance
#  * typevars?
