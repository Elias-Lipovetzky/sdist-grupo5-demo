"""Servidor didactico REST y GraphQL sobre una misma base SQLite."""
import json
import os
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from graphql import build_schema, graphql_sync

DB_PATH = os.environ.get("DB_PATH", "data/demo.sqlite")


@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, name TEXT, email TEXT, address TEXT,
                phone TEXT, bio TEXT);
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id),
                product TEXT, total_cents INTEGER, status TEXT);
            CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id);
        """)
        db.executemany("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)", [
            (1, "Ana", "ana@example.test", "San Martin 100, Ushuaia", "2901-111111", "Cliente frecuente. " * 12),
            (2, "Bruno", "bruno@example.test", "Belgrano 200, Rio Grande", "2964-222222", "Prefiere retirar en sucursal. " * 12),
            (3, "Carla", "carla@example.test", "Roca 300, Tolhuin", "2901-333333", "Solicita entrega por la tarde. " * 12),
        ])
        db.executemany("INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?, ?)", [
            (101, 1, "Teclado", 3500000, "entregado"),
            (102, 1, "Mouse", 1800000, "pendiente"),
            (103, 2, "Monitor", 22000000, "entregado"),
            (104, 3, "Auriculares", 4200000, "pendiente"),
        ])


class Store:
    def __init__(self, db):
        self.db = db
        self.sql = []
        self.orders_cache = None

    def select(self, sql, args=()):
        self.sql.append(sql)
        return [dict(row) for row in self.db.execute(sql, args)]

    def users(self):
        return self.select("SELECT * FROM users ORDER BY id")

    def orders(self, user_id):
        return self.select("SELECT * FROM orders WHERE user_id = ? ORDER BY id", (user_id,))


schema = build_schema("""
    type Query { users: [User!]!, user(id: ID!): User }
    type User {
        id: ID!, name: String!, email: String!, address: String!,
        phone: String!, bio: String!, orders: [Order!]!
    }
    type Order {
        id: ID!, user_id: ID!, product: String!, total_cents: Int!, status: String!
    }
""")


def resolve_orders(user, info):
    store = info.context["store"]
    if info.context["mode"] == "naive":
        return store.orders(user["id"])
    # Carga por lote una vez por request; incluye aliases y usuarios individuales.
    if store.orders_cache is None:
        store.orders_cache = {}
        for order in store.select("SELECT * FROM orders ORDER BY id"):
            store.orders_cache.setdefault(order["user_id"], []).append(order)
    return store.orders_cache.get(user["id"], [])


schema.get_type("Query").fields["users"].resolve = lambda _, info: info.context["store"].users()


def resolve_user(_, info, id):
    rows = info.context["store"].select("SELECT * FROM users WHERE id = ?", (id,))
    return rows[0] if rows else None


schema.get_type("Query").fields["user"].resolve = resolve_user
schema.get_type("User").fields["orders"].resolve = resolve_orders


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, body, store=None):
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-SQL-Queries", str(len(store.sql) if store else 0))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        with connect() as db:
            store = Store(db)
            if path == "/api/v1/users":
                body = store.users()
            elif path == "/api/v1/users-with-orders":
                body = store.users()
                orders = store.select("SELECT * FROM orders ORDER BY id")
                for user in body:
                    user["orders"] = [o for o in orders if o["user_id"] == user["id"]]
            else:
                parts = path.strip("/").split("/")
                if len(parts) not in (4, 5) or parts[:3] != ["api", "v1", "users"] or not parts[3].isdigit() or (len(parts) == 5 and parts[4] != "orders"):
                    self.send_json(404, {"error": "Recurso inexistente"})
                    return
                users = store.select("SELECT * FROM users WHERE id = ?", (int(parts[3]),))
                if not users:
                    self.send_json(404, {"error": "Usuario inexistente"}, store)
                    return
                body = store.orders(int(parts[3])) if len(parts) == 5 else users[0]
            self.send_json(200, body, store)

    def do_POST(self):
        if urlsplit(self.path).path != "/graphql":
            self.send_json(404, {"error": "Recurso inexistente"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("Se requiere un cuerpo de hasta 64 KiB")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or not isinstance(body.get("query"), str):
                raise ValueError("Se requiere query como texto")
            if body.get("variables") is not None and not isinstance(body["variables"], dict):
                raise ValueError("variables debe ser un objeto")
            if body.get("operationName") is not None and not isinstance(body["operationName"], str):
                raise ValueError("operationName debe ser texto")
            mode = self.headers.get("X-Resolver-Mode", "batched")
            if mode not in ("naive", "batched"):
                raise ValueError("X-Resolver-Mode debe ser naive o batched")
        except (ValueError, UnicodeDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
            return
        with connect() as db:
            store = Store(db)
            result = graphql_sync(schema, body["query"], variable_values=body.get("variables"),
                                  operation_name=body.get("operationName"),
                                  context_value={"store": store, "mode": mode})
            response = {"data": result.data}
            if result.errors:
                response["errors"] = [e.formatted for e in result.errors]
            response["extensions"] = {"resolverMode": mode, "sqlQueries": len(store.sql), "sql": store.sql}
            self.send_json(200, response, store)


if __name__ == "__main__":
    initialize()
    print("Demo REST + GraphQL en http://0.0.0.0:8000", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
