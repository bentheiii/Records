RecordBase
==============
.. autoclass:: records.record.RecordBase(object)

    .. autoattribute:: _fields

    .. automethod:: __new__
    .. automethod:: post_new
    .. automethod:: to_dict
    .. automethod:: to_json
    .. automethod:: to_pickle
    .. automethod:: __eq__
    .. automethod:: __hash__
    .. automethod:: __repr__


    **class and static methods**
        .. automethod:: __init_subclass__
        .. automethod:: default_type_check_style
        .. automethod:: from_instance
        .. automethod:: from_json
        .. automethod:: from_json_io
        .. automethod:: from_mapping
        .. automethod:: from_pickle
        .. automethod:: from_pickle_io
        .. automethod:: is_frozen
        .. automethod:: parse
        .. automethod:: pre_bind
        .. automethod:: _to_dict

