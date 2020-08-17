from records.fillers.builtin_fillers.repo import builtin_filler_checkers, builtin_filler_map
from records.fillers.builtin_fillers.std_fillers import (Encoding, Eval, FromInteger, Loose, LooseUnpack,
                                                         LooseUnpackMap, SingletonFromFalsish, Whole,
                                                         std_filler_checkers, std_filler_map)
from records.fillers.builtin_fillers.typing_fillers import typing_checkers
from records.fillers.builtin_validators import Clamp, FullMatch, Truth, Within
from records.fillers.coercers import CallCoercion, ClassMethodCoercion, CoercionToken, ComposeCoercer, MapCoercion
from records.fillers.validators import AssertCallValidation, AssertValidation, CallValidation, ValidationToken

builtin_filler_map.update(std_filler_map)
builtin_filler_checkers.extend(std_filler_checkers)
builtin_filler_checkers.extend(typing_checkers)

__all__ = ['builtin_filler_map', 'builtin_filler_checkers',

           'CoercionToken', 'CallCoercion', 'MapCoercion', 'ClassMethodCoercion', 'ComposeCoercer',
           'ValidationToken', 'AssertValidation', 'CallValidation', 'AssertCallValidation',
           'Clamp', 'Within', 'FullMatch', 'Truth',

           'Eval', 'Loose', 'LooseUnpack', 'LooseUnpackMap', 'Whole', 'FromInteger',
           'SingletonFromFalsish', 'Encoding']
