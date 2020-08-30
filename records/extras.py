"""
This module includes libraries to use that can be overridden by user programs. For instance, to make Records encode and
 decode with `ujson <https://github.com/ultrajson/ultrajson>`_ use the following code::

    import records.extras
    import ujson
    records.extras.json = ujson
"""

import json
import pickle
import re

__all__ = ['json', 'pickle', 're']
