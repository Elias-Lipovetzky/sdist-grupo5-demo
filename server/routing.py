from dataclasses import dataclass
import re


class APIError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    handler: object


class Router:
    def __init__(self, routes):
        self.routes = routes

    def dispatch(self, method, path, store, body, headers):
        for route in self.routes:
            match = re.fullmatch(route.path, path)
            if route.method == method and match:
                return route.handler(store, body, headers, **match.groupdict())
        raise APIError(404, "Ruta inexistente para ese metodo HTTP")
