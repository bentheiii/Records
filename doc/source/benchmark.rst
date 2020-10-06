=========
Benchmark
=========
construction
=============
new_record
-----------
.. code-block:: python

    class REC_Point(RecordBase):
        x: float
        y: float
        z: int = 0
        w: str = ""



    def new_record():
        REC_Point(x=12, y=3, w="hi")

new_dataclass
--------------
.. code-block:: python

    @dataclass
    class PYD_Point:
        x: float
        y: float
        z: int = 0
        w: str = ""



    def new_dataclass():
        PYD_Point(x=12, y=3, w="hi")

results:
--------
============== ==============
usage          runs/sec      
============== ==============
new_dataclass  734,380       
**new_record** **238,729**   
============== ==============

construction_checked
=====================
new_record
-----------
.. code-block:: python

    class REC_Point(RecordBase, default_type_check=check_strict):
        x: float
        y: float
        z: int = 0
        w: str = ""



    def new_record():
        REC_Point(x=12.1, y=3.0, w="hi")

new_pydantic
-------------
.. code-block:: python

    class PYD_Point(BaseModel):
        x: float
        y: float
        z: int = 0
        w: str = ""



    def new_pydantic():
        PYD_Point(x=12, y=3, w="hi")

results:
--------
============== ==============
usage          runs/sec      
============== ==============
new_pydantic   188,558       
**new_record** **127,108**   
============== ==============

tic   100,467       
**new_record** **29,576**    
============== ==============

