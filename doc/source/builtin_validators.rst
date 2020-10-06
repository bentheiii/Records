built-in validators
===================
The following are built in validators in records

.. autoclass:: records.fillers.validators.ValidationToken

.. autoclass:: records.fillers.validators.AssertValidation(ValidationToken, ABC)

    .. automethod:: __init__

    .. automethod:: assert_

.. autoclass:: records.fillers.validators.AssertCallValidation(AssertValidation)

    .. automethod:: __init__

.. autoclass:: records.fillers.validators.CallValidation(AssertValidation)

    .. automethod:: __init__

.. autoclass:: records.fillers.builtin_validators.Clamp(ValidationToken)

    .. automethod:: __init__

.. autoclass:: records.fillers.builtin_validators.Cyclic(ValidationToken)

    .. automethod:: __init__

.. autoclass:: records.fillers.builtin_validators.Within(AssertValidation)

    .. automethod:: __init__

.. autoclass:: records.fillers.builtin_validators.FullMatch(AssertValidation)

    .. automethod:: __init__

.. autoclass:: records.fillers.builtin_validators.Truth(AssertValidation)

    .. automethod:: __init__
