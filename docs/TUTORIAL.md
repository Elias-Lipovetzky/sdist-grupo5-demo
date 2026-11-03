# Cómo presentar el código y ejecutar la demo

Guion breve de cinco minutos. Abrí el editor y una PowerShell en la carpeta del proyecto. En el editor, Ctrl+F permite llegar a los nombres indicados. Queremos mostrar nombre del usuario, producto y total de sus pedidos; REST y GraphQL leen la misma SQLite.

## 1. Preparar antes de la exposición

Cómo llegar: iniciá Docker Desktop y abrí la terminal del proyecto.

```powershell
docker compose up -d --build --wait
docker compose ps
```

La construcción inicial necesita internet. Si ya preparaste la imagen, ejecutá sin descargar ni construir:

```powershell
docker compose up -d --no-build --pull never --wait
```

Docker incluye servidor, cliente y dependencias para repetir el entorno en la VM. SQLite persiste en un volumen. En los siguientes comandos, `-T` desactiva la terminal interactiva porque el cliente no pide entrada.

## 2. REST: seguir un workflow completo

Cómo llegar: abrí `client/cli.py`, buscá `build_parser` y observá que cada subcomando registra su handler. Luego abrí `client/workflows.py` y buscá `demo_rest`.

```python
users = client.get("/api/v1/users")
for user in users:
    orders = client.get(f'/api/v1/users/{user["id"]}/orders')
```

El cliente obtiene usuarios y después pide pedidos por usuario. Se hizo así para evidenciar under-fetching: la primera respuesta no alcanza. Cada comando tiene una función propia con todos los pasos del escenario.

```powershell
docker compose exec -T api python demo.py rest
```

Señalá los cuatro GET y los siete SELECT. Cada ruta de pedidos verifica primero al usuario y luego consulta sus pedidos: son dos SELECT por ruta.

Cómo llegar al servidor: abrí `server/rest_api.py`, buscá `REST_ROUTES` y seguí `list_users` o `list_user_orders`. La tabla conecta método y URL con una función; `server/http_server.py` delega al router sin decidir cada recurso con un bloque de ifs.

<!-- pagebreak -->

## 3. REST agregado: menos viajes, campos sobrantes

Cómo llegar: en `client/workflows.py` buscá `demo_overfetch`; en `server/rest_api.py`, `list_users_with_orders`.

```python
users = store.users()
orders = store.all_orders()
```

El handler reúne usuarios y pedidos en una respuesta. Se agregó para evitar viajes adicionales, pero devuelve email, domicilio y biografía que la vista no necesita: over-fetching. REST podría implementar selección de campos; esta demo no lo hace.

```powershell
docker compose exec -T api python demo.py overfetch
```

## 4. GraphQL: el cliente elige los campos

Cómo llegar: abrí `server/graphql_api.py` y buscá `SCHEMA`. Es el contrato: define tipos, campos y relaciones. `!` indica un valor no nulo. Después abrí `client/workflows.py` y buscá `QUERY` y `demo_graphql`.

```graphql
{ users { name orders { product total_cents } } }
```

La query pide solamente los campos de la vista. Se usa un esquema para validar lo que puede consultar el cliente y resolvers para obtenerlo. Los importes se guardan en centavos.

```powershell
docker compose exec -T api python demo.py graphql
```

Señalá una solicitud HTTP y dos SELECT. `data` contiene los campos pedidos; `extensions` agrega diagnóstico. POST transporta una lectura, no crea un recurso.

Cómo seguir la ejecución: `GRAPHQL_ROUTES` conduce a `execute_query`; `graphql_sync` valida y ejecuta. `create_schema` conecta `users` con `resolve_users` y `orders` con la estrategia elegida.

<!-- pagebreak -->

## 5. N+1: una query puede ejecutar muchos SELECT

Cómo llegar: en `client/workflows.py` buscá `demo_nplus1`; en `server/graphql_api.py`, compará `resolve_orders_naive` y `resolve_orders_batched`.

```python
def resolve_orders_naive(user, info):
    return info.context["store"].orders(user["id"])
```

La estrategia ingenua consulta pedidos por cada usuario: un SELECT de usuarios más tres de pedidos. Se incluyó para mostrar el costo oculto detrás de una sola solicitud HTTP.

```powershell
docker compose exec -T api python demo.py nplus1
```

La estrategia por lote carga todos los pedidos una vez y los agrupa. Fragmento de `resolve_orders_batched`:

```python
if store.orders_cache is None:
    store.orders_cache = {}
    for order in store.all_orders():
        store.orders_cache.setdefault(order["user_id"], []).append(order)
```

Se hizo para reutilizar los resultados durante la misma solicitud. Volvé a ejecutar `graphql`: los datos son iguales y bajan de cuatro SELECT a dos. Esta carga lee todos los pedidos; para un dataset grande habría que filtrar y paginar. No es una implementación de DataLoader.

## 6. Cerrar y responder preguntas

Podés decir: “REST organiza recursos; GraphQL permite elegir campos dentro de un esquema. La flexibilidad exige cuidar el acceso a datos: una solicitud HTTP no garantiza una consulta SQL”. N+1 también puede aparecer en REST.

```powershell
docker compose exec -T api python demo.py error
docker compose exec -T api python demo.py all
docker compose logs --tail 30 api
docker compose down
```

`error` muestra un campo inexistente rechazado sin SQL; es opcional. `all` sirve para ensayar, `logs` muestra el servidor y `down` conserva SQLite. `--full` después del comando muestra textos largos completos. Los bytes se miden antes de abreviar y en GraphQL incluyen diagnóstico; no prueban rendimiento general.
