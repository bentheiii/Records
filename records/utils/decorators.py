from functools import wraps


def decorator_kw_method(func):
    """
    A decorator to apply to other decorator methods, to allow them to delay calling with keyword arguments.
    .. example::
        >>> @decorator_kw_method
        >>> def foo(func, *, a=0):
        >>>     ...
        >>> @foo
        >>> def bar0():
        >>>     ...
        >>> @foo(a=3)
        >>> def bar3():
        >>>     ...
    """

    @wraps(func)
    def ret(self, f=None, **kwargs):
        if f is None:
            return lambda f: ret(self, f, **kwargs)
        return func(self, f, **kwargs)

    return ret
