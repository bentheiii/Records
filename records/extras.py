"""
This module includes libraries to use that can be overridden by user programs. For instance, to make Records encode and
decode with `ujson <https://github.com/ultrajson/ultrajson>`_ use the following code::

    import records.extras
    import ujson
    records.extras.json = ujson

All extras default to their standard library implementations. Any overridden members must fully support the default's
API.
"""

import json
import pickle
import re

__all__ = ['json', 'pickle', 're']
