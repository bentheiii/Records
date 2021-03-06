![Test records](https://github.com/bentheiii/Records/workflows/Test%20records/badge.svg?branch=master)
[![codecov](https://codecov.io/gh/bentheiii/Records/branch/master/graph/badge.svg)](https://codecov.io/gh/bentheiii/Records)

# Records
Records is a python library that makes powerful structure classes easy.

[API reference](https://records.readthedocs.io/en/latest/index.html)

## Simplest Example
A feature of Records is that, by default, it does nothing more than a namedtuple or dataclass would.
```python
from records import RecordBase

class Point(RecordBase):
    x: float
    y: float
    z: float = 0.0

p0 = Point(x=0, y=0)
print(p0)  # Point(x=0, y=0)
print(p0.x)  # 0
# note that no type checking or coercion is performed
print(type(p0.y))  # int
# by default, the type hints are not even run
p1 = Point(x="hello", y="world", z="1.0")
print(p1.y)  # world
print(type(p1.z))  # str
```

## Checking, Coercion, and Validation
Sometimes we'd like to perform some additional processing to arguments before they are entered into the struct. For that we have three steps: type-checking, coercion, and validation
* type-checking is the first and simplest step, it simply checks that the argument is of the type we expect. If it isn't, then we perform coercion.
* type coercion only occurs if typechecking has failed, it will attempt to convert the into the type we expect. As one may expect, there is a large number of potential coercers, so they must be added each individually.
* validation occurs after either type checking or type coercion have succeeded. By this point we are certain that the input is of the correct type and we want to ensure/manipulate its value.

These methods are described per-field with the `Annotation` type hint (`Annotation` is new in python 3.9, but has been backported by `records` for older versions to use)

These three steps are expanded upon in the documentation, for now we will show some brief examples:
```python
from typing import List
from records import RecordBase, Annotated, check, check_strict, Loose, Within, Eval

class Person(RecordBase):
    first_name: str  # no coercion or checking here, this is what we call a "hollow" field
    last_name: Annotated[str, check]  # now we will raise a TypeError if anyone tries to enter a non-string last_name  
    year_of_birth: Annotated[int, check_strict]  # we will raise a TypeError if year_of_birth isn't exactly an int (so passing True will throw an error)
    lucky_number: Annotated[int, check, Loose]  # the "Loose" built-in coerser will simply call the destination type with the input as an argument, so that using `lucky_number="7"` would be equivalent to `lucky_number=int("7")`
    number_of_children: Annotated[int, check, Within(ge=0)]  # the Within built-in validator ensures the value is within stated bounds (in this case, at least zero)
    # field tokens can even be more complex in case of nested field types
    names_of_children: Annotated[List[Annotated[int, check, Eval]], check]  # the list will be checked to be a list, and each item individually will be checked or coerced to be an int using the built-in Eval coercer.
    
    # validators can also be added after declaration with pre_bind
    @classmethod
    def pre_bind(cls):
        @cls.last_name.add_validator
        def no_bad_words(last_name):
            # we want to remove some words from the last name
            return last_name.replace('richard', '*******')

    # we can also add some more pre-processing on an entire instance with "post_new"
    def post_new(self):
        if len(self.names_of_children) != self.number_of_children:
            raise ValueError("children mismatch")
```
## Parsing
Records can also be parsed from various python primitives. Including parsing from `dict`s, jsons, and even generic namepaces.
```python
from types import SimpleNamespace
from records import RecordBase, check

class User(RecordBase, default_type_check=check):
    name: str
    password: str
    age: int = 18
    

print(User.from_mapping({"name": "richard", "password": "swordfish"}))
print(User.from_json('{"name": "richard", "password": "swordfish"})'))
n = SimpleNamespace(user="rich", password="ard", age= 7)
print(User.from_instance(n))

# parsing can even be done if you expect misnamed fields!
from_upper_dict = User.from_mapping.select(keys_to_rename=[('user','name')], keys_to_remove=['favorite_color'])
print(from_upper_dict({'user':'richard', 'password': 'pw', 'favorite_color': 'red'}))
```

You can also define your own parsers and even use them in construction!
```python
from math import sqrt
from records import RecordBase, check, SelectableFactory, parser

class Point(RecordBase, default_type_check=check):
    x: float
    y: float
    z: float = 0
    
    @parser
    @SelectableConstructor
    @classmethod
    def from_tuple(cls, v):
        return {'x':v[0], 'y':v[1], 'z':v[2] if len(v) > 2 else 0}

    @property
    def norm(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2)

p = Point([2,3,6])
print(p.norm)  # 7
```
## Exporting
Records can also be exporting to various formats (same as parsing).
```python
from records import RecordBase, check

class Point(RecordBase, default_type_check=check):
    x: float
    y: float
    z: float

p = Point(x=2, y=3, z=6)
print(p.to_dict())
print(p.to_pickle())
#  again, we can select to change the keys
print(
    p.to_json.select(keys_to_add=[('w',0)])()
)
```