from dataclasses import fields
from pydantic import (
    BaseModel,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typing import Optional, Iterable, Tuple, List
from enum import Enum
from .datatypes import (
    OrderEnum,
    SearchFieldModel,
    SearchPatternEnum,
    SearchPatternModel,
    OrderFieldModel,
    FilterFieldModel,
    RequestFielterModel,
)

orders = ["asc", "desc"]
default_search_pattern = "{}%"
not_included_fields = "{not_included_fields}"


class QueryModel(BaseModel):
    query: str
    base_params: Optional[dict] = {}

    search_value: Optional[str] = None
    search_field: Optional[str] = None
    strict_search: Optional[bool] = False

    order_field: Optional[str] = None
    order: Optional[OrderEnum] = OrderEnum.desc

    page: Optional[int] = 1
    page_size: Optional[int] = 15

    search_fields: List[SearchFieldModel] = []
    search_patterns: List[SearchPatternModel] = []

    order_fields: List[OrderFieldModel] = []
    default_order_field: str
    default_order: OrderEnum = OrderEnum.desc

    allowed_filters: List[FilterFieldModel] = []
    filters: List[RequestFielterModel] = []

    __query_params: Optional[dict] = {}
    __total_params: Optional[dict] = {}

    @property
    def __page_start(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def __page_end(self) -> int:
        return self.__page_start + self.page_size

    @property
    def __search_names_list(self) -> List[str]:
        return [search_field.name for search_field in self.search_fields]

    @property
    def __order_names_list(self) -> List[str]:
        return [order_field.name for order_field in self.order_fields]

    @property
    def __filter_names_list(self) -> List[str]:
        return [filter.name for filter in self.allowed_filters]

    @property
    def current_search_field(self) -> SearchFieldModel:
        for sf in self.search_fields:
            if sf.name == self.search_field:
                return sf
        raise ValueError(
            f'search_field value "{self.search_field}" must be in search_fields {self.__search_names_list}'
        )

    @property
    def current_order_field(self) -> OrderFieldModel:
        for of in self.order_fields:
            if of.name == self.order_field:
                return of
        raise ValueError(
            f'order_field value "{self.order_field}" must be in order_fields {self.__order_names_list}'
        )

    @field_validator("page", "page_size")
    @classmethod
    def validate_page_and_page_size(cls, value, hendler: ValidationInfo) -> int:
        return value if value > 1 else 1

    @field_validator("strict_search")
    @classmethod
    def validate_strict_search(cls, value, hendler: ValidationInfo) -> int:
        return True if value in [True, 1, "1"] else False

    @field_validator("search_field", "order_field")
    @classmethod
    def validate_search_and_order_fields(cls, value, hendler: ValidationInfo) -> int:
        return value.strip().lower() if value else None

    @model_validator(mode="after")
    def validate_model(self):
        if self.search_field and self.search_field not in self.__search_names_list:
            raise ValueError(
                f'search_field value "{self.search_field}" not in search_fields {self.__search_names_list}'
            )

        if self.order_field and self.order_field not in self.__order_names_list:
            raise ValueError(
                f'order_field value "{self.order_field}" not in order_fields {self.__order_names_list}'
            )

        for pattern in self.search_patterns:
            if pattern.field_name not in self.__search_names_list:
                raise ValueError(
                    f"Can not apply search pattert {pattern}. Pattern {pattern.field_name} not in {self.__search_names_list}"
                )

        for filter in self.filters:
            if filter.field not in self.__filter_names_list:
                raise ValueError(
                    f'Can not apply filter "{filter.field}". Filter "{filter.field}" not in {self.__filter_names_list}'
                )
            for af in self.allowed_filters:
                if filter.field == af.name and not all(
                    [v in af.allowed_values for v in filter.values]
                ):
                    raise ValueError(
                        f'Can not apply filter "{filter.field}" with values {filter.values}. Value not in {af.allowed_values}'
                    )

        return self

    class Config:
        validate_assignment = True

    def __get_search_pattern_by_field_name(self, field_name):
        for p in self.search_patterns:
            if p.field_name == field_name:
                return p.pattern
        return SearchPatternEnum.start

    def __get_filter_fields_from_request(self, request):
        filters = []
        for possible_filter in self.allowed_filters:
            f_values = request.params.get(possible_filter.name)
            if not f_values:
                continue
            f_values = [
                f for f in f_values.split(",") if f in possible_filter.allowed_values
            ]
            if f_values:
                filters.append(
                    RequestFielterModel(field=possible_filter.field, values=f_values)
                )
        self.filters = filters

    def __get_search_value_and_field_from_request(self, request):
        self.search_value = request.params.get("search_value")
        self.search_field = request.params.get("search_field")
        self.strict_search = request.params.get("strict")

    def __get_order_value_and_field_from_request(self, request):
        self.order_field = request.params.get("order_field", self.default_order_field)
        self.order = request.params.get("order", self.default_order)

    def __get_page_and_page_size_from_request(self, request):
        self.page = request.params.get("page", self.page)
        self.page_size = request.params.get("page_size", self.page_size)

    def process_request(self, request):
        self.__get_page_and_page_size_from_request(request)
        self.__get_order_value_and_field_from_request(request)
        self.__get_filter_fields_from_request(request)
        self.__get_search_value_and_field_from_request(request)

    def generate_query(self):
        self.__query_params = self.base_params.copy()
        self.__total_params = self.base_params.copy()

        self.__query_params["page_start"] = self.__page_start
        self.__query_params["page_end"] = self.__page_end

        where = self.__generate_where_part()
        order = self.__generate_order_part()

        full_query = f"""
        SELECT * FROM (
            SELECT a.*, ROWNUM as rnum FROM (
                {self.query}
                {where}
                {order}
            ) a WHERE ROWNUM <= :page_end
        ) 
        WHERE rnum  > :page_start
        """

        total_query = f"""
        SELECT count(*) FROM (
            {self.query}
            {where}
            ) a
        """
        return full_query, self.__query_params, total_query, self.__total_params

    def __generate_where_part(self):
        where = ""
        additional_fields = []
        if self.search_value:
            search_field = self.current_search_field
            if (
                search_field.include_if_not_in_query
                and not_included_fields in self.query
            ):
                if len(search_field.fields) == 1:
                    possible_sub_str = [
                        f"{search_field.fields[0]} as {search_field.name}"
                    ]
                else:
                    possible_sub_str = [
                        f"{f} as {search_field.name}_{f.replace('.', '_')}"
                        for f in search_field.fields
                    ]
                for s in possible_sub_str:
                    if s not in self.query:
                        additional_fields.append(s)
            where = f"""
            {'where' if 'where' not in self.query.lower() else 'and'} (
            {' or '.join([f'lower({f}) like lower(:search_value)' for f in search_field.fields])}
            )
            """

            if self.strict_search:
                pattern = SearchPatternEnum.strict
            else:
                pattern = self.__get_search_pattern_by_field_name(self.search_field)

            search_value = pattern.format(self.search_value)

            self.__query_params["search_value"] = search_value
            self.__total_params["search_value"] = search_value
        if additional_fields and not_included_fields in self.query:
            self.query = self.query.format(
                not_included_fields=", ".join([""] + additional_fields)
            )
        else:
            self.query = self.query.format(not_included_fields="")
        where = self.__genetate_filter_part(where_part=where)
        return where

    def __generate_order_part(self):
        order = ""
        if self.order_field:
            order_field = self.current_order_field
            ordering = self.order
            order = f"""
            order by 
            {', '.join([f'{of.field_name} {ordering}' for of in order_field.fields])}
            """
        return order

    def __genetate_filter_part(self, where_part=""):
        if self.filters:
            filters = f"""
            {'where' if ('where' not in self.query.lower() and 'where' not in where_part) else 'and'} (
            {' and '.join([f'lower({f.field}) in {tuple(f.values)}'.replace(',)', ")") for f in self.filters])}
            )
            """
            where_part += filters
        return where_part
