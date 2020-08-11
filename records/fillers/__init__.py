from records.fillers.builtin_fillers.repo import builtin_filler_checkers, builtin_filler_map
from records.fillers.builtin_fillers.std_fillers import (Encoding, Eval, SingletonFromFalsish, FromInteger, Loose,
                                                         LooseUnpack, LooseUnpackMap, Whole, std_filler_checkers,
                                                         std_filler_map)
from records.fillers.builtin_fillers.typing_fillers import typing_checkers
from records.fillers.coercers import CallCoercion, MapCoercion, ComposeCoercer, CoercionToken, ClassMethodCoercion
from records.fillers.builtin_validators import Clamp, Within, FullMatch, Truth
from records.fillers.validators import ValidationToken, AssertValidation, CallValidation, AssertCallValidation

builtin_filler_map.update(std_filler_map)
builtin_filler_checkers.extend(std_filler_checkers)
builtin_filler_checkers.extend(typing_checkers)

__all__ = ['builtin_filler_map', 'builtin_filler_checkers',

           'CoercionToken', 'CallCoercion', 'MapCoercion', 'ClassMethodCoercion', 'ComposeCoercer',
           'ValidationToken', 'AssertValidation', 'CallValidation', 'AssertCallValidation',
           'Clamp', 'Within', 'FullMatch', 'Truth',

           'Eval', 'Loose', 'LooseUnpack', 'LooseUnpackMap', 'Whole', 'FromInteger',
           'SingletonFromFalsish', 'Encoding']
