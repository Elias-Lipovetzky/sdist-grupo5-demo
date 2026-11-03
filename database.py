"""SQLite compartida: inicializacion y consultas medidas por solicitud."""
import os
from contextlib import contextmanager
from pathlib import Path
import sqlite3


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

    def user(self, user_id):
        rows = self.select("SELECT * FROM users WHERE id = ?", (user_id,))
        return rows[0] if rows else None

    def all_orders(self):
        return self.select("SELECT * FROM orders ORDER BY id")
