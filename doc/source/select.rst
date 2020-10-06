select
============
.. automodule:: records.select

    .. autoclass:: Select()

        .. autoattribute:: empty
            :annotation: = Select()

        .. automethod:: __init__
        .. automethod:: merge
        .. automethod:: __call__

    .. autodecorator:: SelectableFactory

        .. autofunction:: records.select.SelectableFactory.Bound.select

    .. autodecorator:: Exporter

        .. autofunction:: records.select.Exporter.Bound.select

        .. autofunction:: records.select.Exporter.Bound.export_with

    .. _selection:

    Selection
    ---------
    All :py:class:`selectable factories <SelectableFactory>` and :py:class:`exporters <Exporter>` can be called with
    selection. Selection allows users to treat certain dictionary keys differently. This can be used to create aliases,
    or to hide or synthesize some attributes when exporting or importing from other APIs. Selection is quite intuitive
    and is done with the :py:meth:`SelectableFactory.select <records.select.SelectableFactory.Bound.select>`
    or :py:meth:`Exporter.select <records.select.Exporter.Bound.select>` methods.

    .. code-block:: python

        class A(RecordBase):
            x: int
            y: str

        # when exporting
        a = A(x=5, y='6')
        assert a.to_dict() == {'x': 5, 'y': 6}
        assert a.to_dict.select(keys_to_remove='x')() == {'y': 6}
        select = Select(keys_to_add = {'z': 3})
        assert a.to_dict.select(select, keys_to_rename={'x':'X'}) == {'X': 5, 'y': 6, 'z': 3}

        # when importing
        A.from_dict({'x':5, 'y': '6'}) == a
        A.from_dict.select(keys_to_add={'x': 5})({'y': 6}) == a
        select = Select(keys_to_remove = 'z')
        A.from_dict.select(select, keys_to_rename={'X': 'x'})({'X': 5, 'y': 6, 'z': 3}) == a