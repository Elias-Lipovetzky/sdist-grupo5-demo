from routing import APIError, Route


def health(store, body, headers):
    return {"status": "ok"}


def list_users(store, body, headers):
    return store.users()


def get_user(store, body, headers, user_id):
    user = store.user(int(user_id))
    if user is None:
        raise APIError(404, "Usuario inexistente")
    return user


def list_user_orders(store, body, headers, user_id):
    get_user(store, body, headers, user_id)
    return store.orders(int(user_id))


def list_users_with_orders(store, body, headers):
    users = store.users()
    orders = store.all_orders()
    for user in users:
        user["orders"] = [order for order in orders if order["user_id"] == user["id"]]
    return users


REST_ROUTES = [
    Route("GET", r"/health", health),
    Route("GET", r"/api/v1/users", list_users),
    Route("GET", r"/api/v1/users/(?P<user_id>[0-9]+)", get_user),
    Route("GET", r"/api/v1/users/(?P<user_id>[0-9]+)/orders", list_user_orders),
    Route("GET", r"/api/v1/users-with-orders", list_users_with_orders),
]
