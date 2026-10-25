"""Cliente de terminal sin dependencias adicionales. Corre dentro del contenedor."""
import argparse
import json
from urllib.request import Request, urlopen

QUERY = "{ users { name orders { product total_cents } } }"


def request(base, path, query=None, mode="batched"):
    data = json.dumps({"query": query}).encode() if query else None
    print(f"\n{'POST' if data else 'GET'} {path}")
    if query:
        print(f"Query: {query}\nResolver: {mode}")
    req = Request(base + path, data=data, headers={"Content-Type": "application/json", "X-Resolver-Mode": mode})
    with urlopen(req, timeout=10) as response:
        raw = response.read()
        body = json.loads(raw)
        sql = int(response.headers["X-SQL-Queries"])
        print(f"HTTP {response.status} | cuerpo UTF-8: {len(raw)} bytes | SELECT: {sql}")
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return body, len(raw), sql


def run(base, step):
    if step == "rest":
        users, size, sql = request(base, "/api/v1/users")
        view = []
        for user in users:
            orders, n, q = request(base, f'/api/v1/users/{user["id"]}/orders')
            size += n
            sql += q
            view.append({"name": user["name"], "orders": [{k: o[k] for k in ("product", "total_cents")} for o in orders]})
        print("\nVista que necesitaba el cliente:")
        print(json.dumps(view, indent=2, ensure_ascii=False))
        print(f"TOTAL: {1 + len(users)} requests HTTP | {size} bytes de cuerpos | {sql} SELECT")
    elif step == "overfetch":
        request(base, "/api/v1/users-with-orders")
        print("\nUn GET agregado resuelve los viajes, pero devuelve email, domicilio, bio y otros campos innecesarios.")
    elif step in ("graphql", "nplus1"):
        request(base, "/graphql", QUERY, "naive" if step == "nplus1" else "batched")
    elif step == "error":
        request(base, "/graphql", "{ users { name password } }")
        print("\nHTTP 200 no garantiza exito GraphQL: revisar errors. La validacion rechazo el campo sin consultar SQLite.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=["rest", "overfetch", "graphql", "nplus1", "error", "all"])
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()
    for step in (["rest", "overfetch", "graphql", "nplus1", "error"] if args.step == "all" else [args.step]):
        print(f"\n{'=' * 18} {step.upper()} {'=' * 18}")
        run(args.base, step)
