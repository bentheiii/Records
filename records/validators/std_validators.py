from typing import Type


def check(t: Type):
    def ret(v):
        if isinstance(v, t):
            return v
        raise TypeError(f'must be a {t.__name__} (got {type(v).__name__})')

    ret.__name__ = f'{t.__name__}_checker'


def check_strict(t: Type):
    def ret(v):
        if type(v) == t:
            return v
        raise TypeError(f'must be exactly {t.__name__} (got {type(v).__name__})')

    ret.__name__ = f'{t.__name__}_strict_checker'
