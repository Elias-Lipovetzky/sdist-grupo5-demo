import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from database import Store, connect, initialize
from graphql_api import GRAPHQL_ROUTES
from rest_api import REST_ROUTES
from routing import APIError, Router

router = Router([*REST_ROUTES, *GRAPHQL_ROUTES])


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

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("Se requiere un cuerpo de hasta 64 KiB")
            return json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError) as exc:
            raise APIError(400, str(exc)) from exc

    def handle_request(self, body=None):
        with connect() as db:
            store = Store(db)
            try:
                result = router.dispatch(self.command, urlsplit(self.path).path,
                                         store, body, self.headers)
                self.send_json(200, result, store)
            except APIError as exc:
                self.send_json(exc.status, {"error": str(exc)}, store)

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        try:
            body = self.read_json()
        except APIError as exc:
            self.send_json(exc.status, {"error": str(exc)})
            return
        self.handle_request(body)


if __name__ == "__main__":
    initialize()
    print("Demo REST + GraphQL en http://0.0.0.0:8000", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
