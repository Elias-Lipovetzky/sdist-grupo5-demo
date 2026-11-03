from graphql import build_schema, graphql_sync
from .routing import APIError, Route

SCHEMA = """
    type Query { users: [User!]!, user(id: ID!): User }
    type User {
        id: ID!, name: String!, email: String!, address: String!,
        phone: String!, bio: String!, orders: [Order!]!
    }
    type Order {
        id: ID!, user_id: ID!, product: String!, total_cents: Int!, status: String!
    }
"""


def resolve_users(root, info):
    return info.context["store"].users()


def resolve_user(root, info, id):
    return info.context["store"].user(id)


def resolve_orders_naive(user, info):
    """Una consulta por usuario: produce N+1 al recorrer users."""
    return info.context["store"].orders(user["id"])


def resolve_orders_batched(user, info):
    """Una carga de pedidos por solicitud, reutilizada por todos los usuarios."""
    store = info.context["store"]
    if store.orders_cache is None:
        store.orders_cache = {}
        for order in store.all_orders():
            store.orders_cache.setdefault(order["user_id"], []).append(order)
    return store.orders_cache.get(user["id"], [])


def create_schema(orders_resolver):
    schema = build_schema(SCHEMA)
    schema.get_type("Query").fields["users"].resolve = resolve_users
    schema.get_type("Query").fields["user"].resolve = resolve_user
    schema.get_type("User").fields["orders"].resolve = orders_resolver
    return schema


# Contrato identico; solo cambia el resolver. No mutar durante requests.
SCHEMAS = {
    "naive": create_schema(resolve_orders_naive),
    "batched": create_schema(resolve_orders_batched),
}


def execute_query(store, body, headers):
    if not isinstance(body, dict) or not isinstance(body.get("query"), str):
        raise APIError(400, "Se requiere query como texto")

    if body.get("variables") is not None and not isinstance(body["variables"], dict):
        raise APIError(400, "variables debe ser un objeto")

    if body.get("operationName") is not None and not isinstance(body["operationName"], str):
        raise APIError(400, "operationName debe ser texto")

    mode = headers.get("X-Resolver-Mode", "batched")
    if mode not in SCHEMAS:
        raise APIError(400, "X-Resolver-Mode debe ser naive o batched")
    result = graphql_sync(
        SCHEMAS[mode], body["query"], variable_values=body.get("variables"),
        operation_name=body.get("operationName"), context_value={"store": store},
    )
    response = {"data": result.data}
    if result.errors:
        response["errors"] = [error.formatted for error in result.errors]
    response["extensions"] = {"resolverMode": mode, "sqlQueries": len(store.sql), "sql": store.sql}
    return response


GRAPHQL_ROUTES = [Route("POST", r"/graphql", execute_query)]
