from dataclasses import dataclass
import json
from urllib.request import Request, urlopen


def compact(value):
    if isinstance(value, dict):
        return {key: compact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [compact(item) for item in value]
    if isinstance(value, str) and len(value) > 100:
        return value[:75] + f"... [{len(value)} caracteres]"
    return value


def show_json(value, full=False):
    print(json.dumps(value if full else compact(value), indent=2, ensure_ascii=False))


@dataclass
class Reply:
    body: object
    size: int
    sql: int


class DemoClient:
    def __init__(self, base, full=False):
        self.base = base.rstrip("/")
        self.full = full
        self.replies = []

    def send(self, path, payload=None, mode="batched"):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        print(f"\n{'POST' if data is not None else 'GET'} {path}")
        if payload is not None:
            print(f'Query: {payload["query"]}\nResolver: {mode}')
        req = Request(self.base + path, data=data, headers={
            "Content-Type": "application/json", "X-Resolver-Mode": mode})
        with urlopen(req, timeout=10) as response:
            raw = response.read()
            reply = Reply(json.loads(raw), len(raw), int(response.headers["X-SQL-Queries"]))
            print(f"HTTP {response.status} | cuerpo UTF-8: {reply.size} bytes | SELECT: {reply.sql}")
        self.replies.append(reply)
        show_json(reply.body, self.full)
        return reply

    def get(self, path):
        return self.send(path).body

    def query(self, query, mode="batched", allow_errors=False):
        body = self.send("/graphql", {"query": query}, mode).body
        if body.get("errors") and not allow_errors:
            raise RuntimeError("GraphQL devolvio errores: revisar la respuesta")
        return body

    def summary(self):
        print(f"\nTOTAL: {len(self.replies)} requests HTTP | "
              f"{sum(r.size for r in self.replies)} bytes de cuerpos | "
              f"{sum(r.sql for r in self.replies)} SELECT")


def stage(number, title):
    print(f"\n{number}. {title}")


def introduction(name):
    print(f"\n{'=' * 16} {name} {'=' * 16}")
    print("Vista objetivo: nombre del usuario, producto y total de sus pedidos.")
    print("Textos largos abreviados en pantalla; --full muestra todo. Bytes medidos sobre el cuerpo original.")
