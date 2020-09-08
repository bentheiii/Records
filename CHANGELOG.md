# Records Changelog
# 0.1.0 - unreleased
## added
* sub-fillers: `add_validator` and similar field methods can now be called with `sub_key` to specify a specific sub-filler, as specified by the filler class.
* if sub-fillers of a union filler return identical values at equal `tcp`, an error is not raised.
* package attribute `__version__` to store the library's version string.
# 0.0.1 - 2020/7/9
* initial release