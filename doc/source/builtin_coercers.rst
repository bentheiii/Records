built-in coercers
===================
The following are built in validators in records

.. autoclass:: records.fillers.coercers.CoercionToken

.. autoclass:: records.fillers.coercers.CallCoercion(CoercionToken)

    .. automethod:: __init__

.. autoclass:: records.fillers.coercers.MapCoercion(CoercionToken)

    .. automethod:: __init__

.. autoclass:: records.fillers.coercers.ClassMethodCoercion(CoercionToken)

    .. automethod:: __init__

.. autoclass:: records.fillers.coercers.ComposeCoercer(CoercionToken)

    .. automethod:: __init__

.. autoclass:: records.fillers.builtin_fillers.std_fillers.Eval(CoercionToken)

    .. automethod:: __init__

.. autoclass:: records.fillers.builtin_fillers.std_fillers.LiteralEval(CoercionToken)

.. autoclass:: records.fillers.builtin_fillers.std_fillers.Loose(CoercionToken)

    .. automethod:: __init__

    .. automethod:: constrain

.. autoclass:: records.fillers.builtin_fillers.std_fillers.LooseUnpack(CoercionToken)

    .. automethod:: __init__

    .. automethod:: constrain

.. autoclass:: records.fillers.builtin_fillers.std_fillers.LooseUnpackMap(CoercionToken)

    .. automethod:: __init__

    .. automethod:: constrain

.. autoclass:: records.fillers.builtin_fillers.std_fillers.Whole(CoercionToken)

    .. automethod:: __init__

.. autoclass:: records.fillers.builtin_fillers.std_fillers.ToBytes(CoercionToken)

    .. automethod:: __init__

.. autoclass:: records.fillers.builtin_fillers.std_fillers.FromInteger(CoercionToken)

.. autoclass:: records.fillers.builtin_fillers.std_fillers.Falsish(CoercionToken)

    .. automethod:: __init__