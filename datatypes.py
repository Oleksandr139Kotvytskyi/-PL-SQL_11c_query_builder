from pydantic import (
    BaseModel,
)
from typing import Optional, Iterable, Tuple, List
from enum import Enum


class OrderEnum(str, Enum):
    asc = "asc"
    desc = "desc"


class SearchPatternEnum(str, Enum):
    start = "{}%"
    end = "%{}"
    all = "%{}%"
    strict = "{}"


class SearchPatternModel(BaseModel):
    """
    used for defining search pattern for the field
    default pattern is SearchPatternEnum.start ('{}%')

    example 1:
        usage - SearchPatternModel(name='locations', pattern=SearchPatternEnum.start)
        result sql - "... where locations like 'value%' ..."
    example 2:
        usage - SearchPatternModel(name='locations', pattern=SearchPatternEnum.end)
        result sql - "... where locations like '%value' ..."
    example 3:
        usage - SearchPatternModel(name='locations', pattern=SearchPatternEnum.all)
        result sql - "... where locations like '%value%' ..."
    """

    field_name: str
    pattern: Optional[SearchPatternEnum] = SearchPatternEnum.start


class SearchFieldModel(BaseModel):
    """
    using for define searching for fields
    example 1:
        usage - SearchFieldModel(name='locations', fields=('locations', ))
        result sql - "... where locations like 'your value' ..."
    example 2:
        usage - SearchFieldModel(name='main', fields=('name', 'id',))
        result sql - "... where (name like 'your value' or id like 'your value') ..."
    """

    name: str
    fields: Tuple[str, ...]
    include_if_not_in_query: bool = False


class FilterFieldModel(BaseModel):
    """
    using for define filtert for fields (aplied after search)
    example 1:
        usage - FilterFieldModel(name='locations', field='locations', allowed_values=('a', 'b', ...))
        result sql - "... where locations = 'your value' ..."
    """

    name: str
    field: str
    allowed_values: List[str]


class RequestFielterModel(BaseModel):
    field: str
    values: List[str]


class OrderSingleFieldModel(BaseModel):
    field_name: str
    order: OrderEnum = OrderEnum.desc


class OrderFieldModel(BaseModel):
    """
    using for define ordering for fields
    example 1:
        usage - OrderFieldModel(name='locations', fields=(OrderPattenrModel(filed_name='locations'), ))
        result sql - "... order by locations desc"

    example 2:
        usage - OrderFieldModel(
            name='main',
            fields=(
                OrderPattenrModel(field_name='name'),
                OrderPattenrModel(field_name='id', order=OrderEnum.asc),
            )
        result sql - "... order by name desc, id asc"
    """

    name: str
    fields: Tuple[OrderSingleFieldModel, ...]
