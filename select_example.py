from . import QueryModel, not_included_fields
from .datatypes import (
    OrderEnum,
    SearchPatternEnum,
    SearchPatternModel,
    SearchFieldModel,
    OrderFieldModel,
    OrderSingleFieldModel,
)


def get_list_query2():
    base_sql = f"""
        select id , name, phones, sendkomm as address,
        from users
    """

    search_fields = [
        SearchFieldModel(
            name="main",
            fields=(
                "id",
                "name",
            ),
        ),
        SearchFieldModel(name="phones", fields=("phones",)),
        SearchFieldModel(name="address", fields=("sendkomm",)),
    ]
    search_pattern = [
        SearchPatternModel(field_name="phones", pattern=SearchPatternEnum.all),
        SearchPatternModel(field_name="address", pattern=SearchPatternEnum.all),
    ]
    order_fields = [
        OrderFieldModel(
            name="id",
            fields=(OrderSingleFieldModel(field_name="id", order=OrderEnum.desc),),
        ),
        OrderFieldModel(
            name="name",
            fields=(OrderSingleFieldModel(field_name="name", order=OrderEnum.desc),),
        ),
        OrderFieldModel(
            name="phone",
            fields=(
                OrderSingleFieldModel(field_name="phones", order=OrderEnum.desc),
                OrderSingleFieldModel(field_name="sendkomm", order=OrderEnum.desc),
            ),
        ),
    ]
    query = QueryModel(
        query=base_sql,
        search_fields=search_fields,
        search_patterns=search_pattern,
        order_fields=order_fields,
        default_order_field="id",
        default_order=OrderEnum.desc,
    )
    return query


# Example 1
# called endpoint {{base_url}}/users/?order_field=cid&order=asc&search_field=phones&page=1&page_size=35&search_value=1387
#
# generated params :
#
# {'page_start': 0, 'page_end': 35, 'search_value': '%1387%'}
#
# Generated SQL:
#
# SELECT * FROM (
#     SELECT a.*, ROWNUM as rnum FROM (
#
#       select id , name, phones, sendkomm as address,
#       from users
#
#     where (
#     lower(us.phones) like lower(:search_value)
#     )
#
#     order by
#     us.cid asc
#
#     ) a WHERE ROWNUM <= :page_end
# )
# WHERE rnum  > :page_start
#
#
# Example 2
# called endpoint {{base_url}}/users/?search_field=main&page=1&page_size=10&search_value=275
#
# generated params :
#
# {'page_start': 0, 'page_end': 35, 'search_value': '%1387%'}
#
# Generated SQL:
#
# SELECT * FROM (
#     SELECT a.*, ROWNUM as rnum FROM (
#
#       select id , name, phones, sendkomm as address,
#       from users
#
#       where (
#           lower(id) like lower(:search_value) or lower(name) like lower(:search_value)
#       )
#
#
#       order by
#       us.cid desc
#
#     ) a WHERE ROWNUM <= :page_end
# )
# WHERE rnum  > :page_start
#
#
