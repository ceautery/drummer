from typing import Any

class GraphQLResolveInfo: ...

class GraphQLField:
    resolve: Any

class GraphQLObjectType:
    fields: dict[str, GraphQLField]

class GraphQLSchema:
    query_type: GraphQLObjectType | None
    type_map: dict[str, Any]

class GraphQLError:
    formatted: dict[str, Any]

class ExecutionResult:
    data: dict[str, Any] | None
    errors: list[GraphQLError] | None

def build_schema(source: str, /, *args: Any, **kwargs: Any) -> GraphQLSchema: ...
def graphql_sync(
    schema: GraphQLSchema,
    source: str,
    /,
    *args: Any,
    variable_values: dict[str, Any] | None = ...,
    **kwargs: Any,
) -> ExecutionResult: ...
