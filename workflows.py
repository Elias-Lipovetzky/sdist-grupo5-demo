"""Un workflow completo por comando: abrir una funcion para seguir el escenario."""
from demo_client import DemoClient, introduction, show_json, stage

QUERY = "{ users { name orders { product total_cents } } }"


def demo_rest(args):
    introduction("REST")
    client = DemoClient(args.base, args.full)
    stage(1, "Obtener usuarios: la respuesta no incluye sus pedidos")
    users = client.get("/api/v1/users")
    stage(2, "Completar la informacion: un GET de pedidos por cada usuario")
    view = []
    for user in users:
        orders = client.get(f'/api/v1/users/{user["id"]}/orders')
        view.append({"name": user["name"], "orders": [
            {"product": order["product"], "total_cents": order["total_cents"]}
            for order in orders]})
    stage(3, "Armar en el cliente la vista que necesitabamos")
    show_json(view)
    stage(4, "Interpretar el costo")
    client.summary()
    print("Under-fetching: el primer GET no alcanza. Over-fetching: llegan campos sobrantes.")
    print("Cada ruta de pedidos hace dos SELECT: verifica usuario y consulta pedidos.")


def demo_overfetch(args):
    introduction("OVERFETCH")
    client = DemoClient(args.base, args.full)
    stage(1, "Pedir un recurso agregado: usuarios con todos sus pedidos")
    users = client.get("/api/v1/users-with-orders")
    stage(2, "Comparar lo recibido con los campos necesarios")
    print(f"Recibimos {len(users)} usuarios con pedidos, pero tambien email, domicilio y biografia.")
    stage(3, "Interpretar el costo")
    client.summary()
    print("Un GET evita viajes adicionales, pero el contrato sigue devolviendo datos de mas.")
    print("REST tambien podria ofrecer seleccion de campos; no esta implementada aqui.")


def demo_graphql(args):
    introduction("GRAPHQL")
    client = DemoClient(args.base, args.full)
    stage(1, "Elegir solo los campos de la vista dentro del esquema")
    print(QUERY)
    stage(2, "Enviar una query y resolver pedidos mediante carga por lote")
    result = client.query(QUERY, mode="batched")
    stage(3, "Interpretar la respuesta y el costo")
    print(f'Vista completa: {len(result["data"]["users"])} usuarios, sin campos sobrantes en data.')
    client.summary()
    print("Dos SELECT: usuarios y pedidos. extensions agrega diagnostico a la respuesta.")


def demo_nplus1(args):
    introduction("NPLUS1")
    client = DemoClient(args.base, args.full)
    stage(1, "Mantener la misma query y cambiar solo la estrategia del resolver")
    print(QUERY)
    stage(2, "Resolver pedidos por separado para cada usuario")
    result = client.query(QUERY, mode="naive")
    stage(3, "Identificar N+1 en las consultas SQL")
    count = len(result["data"]["users"])
    client.summary()
    print(f"1 SELECT de usuarios + {count} SELECT de pedidos = {1 + count} SELECT.")
    print("Una solicitud HTTP no garantiza una consulta SQL. Comparar con el comando graphql.")


def demo_error(args):
    introduction("ERROR")
    client = DemoClient(args.base, args.full)
    stage(1, "Pedir un campo que no pertenece al contrato")
    invalid_query = "{ users { name password } }"
    stage(2, "Enviar la query y observar la validacion del esquema")
    result = client.query(invalid_query, allow_errors=True)
    if not result.get("errors"):
        raise RuntimeError("Se esperaba un error de validacion")
    stage(3, "Interpretar el error antes de acceder a datos")
    client.summary()
    print("HTTP 200 no garantiza exito GraphQL: revisar errors. No se ejecuto SQL.")


def demo_all(args):
    """Secuencia para ensayo; en la exposicion ejecutar los comandos por separado."""
    demo_rest(args)
    demo_overfetch(args)
    demo_graphql(args)
    demo_nplus1(args)
    demo_error(args)
