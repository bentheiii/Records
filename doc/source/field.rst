field
============

.. automodule:: records.field

    .. autoclass:: Factory
    .. autoclass:: RecordField

        .. autoattribute:: filler
        .. autoattribute:: name
        .. autoattribute:: owner
        .. autoattribute:: tags

        .. automethod:: __init__
        .. automethod:: add_coercer
        .. automethod:: add_assert_validator
        .. automethod:: add_validator
        .. automethod:: from_type_hint
        .. autoproperty:: has_default
        .. automethod:: is_default
        .. automethod:: make_default

    .. autoclass:: FieldDict(Dict[str, RecordField])

        .. automethod:: filter_by_tag

