from functools import wraps


def decorator_kw_method(func):
    @wraps(func)
    def ret(self, f=None, **kwargs):
        if f is None:
            return lambda f: ret(self, f, **kwargs)
        return func(self, f, **kwargs)

    return ret
