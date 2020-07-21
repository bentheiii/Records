from collections import defaultdict
from typing import Sequence, Generator, Union, Literal

from records.fillers.filler import Filler, TypeCheckStyle, FillingIntent, AnnotatedFiller
from records.utils.typing_compatible import get_args, get_origin


# noinspection PyAbstractClass
class PartialFill(Generator):
    def __init__(self, inner: Generator, origin):
        self.origin = origin
        self.inner = inner
        self.latest = next(inner)

    def send(self, value):
        self.latest = self.inner.send(value)
        return self.latest

    def throw(self, typ, val=..., tb=...):
        self.latest = self.inner.throw(typ, val, tb)
        return self.latest


class UnionFiller(AnnotatedFiller):
    def __init__(self, origin, args):
        super().__init__(origin, args)
        self.sub_types = get_args(origin)
        self.sub_fillers: Sequence[Filler] = ()

    def fill(self, arg):
        pending = [PartialFill(sf.fill(arg), org) for sf, org in zip(self.sub_fillers, self.sub_types)]

        while pending:
            current_score = float('inf')
            current = []
            rest = []

            for sg in pending:
                if sg.latest < current_score:
                    rest.extend(current)
                    current = [sg]
                    current_score = sg.latest
                elif sg.latest > current_score:
                    rest.append(sg)
                else:
                    rest.append(sg)

            pending = rest
            good_typechecks = []
            yield current_score
            for c in current:
                try:
                    intent = next(c)
                except (TypeError, OverflowError, ValueError):
                    pass
                else:
                    if intent == FillingIntent.attempt_validation:
                        good_typechecks.append(c)
                    pending.append(c)
            if good_typechecks:
                break
        else:
            raise TypeError('no type checkers matched')

        good_validations = []
        yield FillingIntent.attempt_validation
        for c in good_typechecks:
            try:
                next(c)
            except StopIteration as e:
                good_validations.append((c.origin, e.value))
            except Exception as e:
                pass
            else:
                raise BaseException(f'filler of origin {c.origin} did not return or raise after validation')

        if not good_validations:
            raise ValueError('no validators succeeded')
        elif len(good_validations) > 1:
            raise ValueError(f'multiple validator success: {[gvt for (gvt, _) in good_validations]}')
        return good_validations[0][-1]

    def bind(self, owner_cls):
        super().bind(owner_cls)
        if self.type_checking_style != TypeCheckStyle.hollow:
            raise TypeError('unions can only be used with hollow type checking')

    type_check = type_check_strict = None


class LiteralFiller(AnnotatedFiller):
    def __init__(self, origin, args):
        super().__init__(origin, args)
        self.possible_values = defaultdict(set)
        for pv in get_args(origin):
            self.possible_values[type(pv)].add(pv)

    def type_check(self, v) -> bool:
        return isinstance(v, tuple(self.possible_values))

    def type_check_strict(self, v) -> bool:
        return type(v) in self.possible_values

    def bind(self, owner_cls):
        super().bind(owner_cls)

        @self.validators.append
        def inner_validator(v):
            if v not in self.possible_values[type(v)]:
                raise ValueError
            return v


typing_checkers = []


@typing_checkers.append
def _typing(stored_type):
    if get_origin(stored_type) == Union:
        return UnionFiller
    if get_origin(stored_type) == Literal:
        return LiteralFiller
