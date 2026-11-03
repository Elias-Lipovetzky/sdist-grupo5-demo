# Grupo 5: REST y GraphQL

Demo de terminal con Python 3.13, SQLite, Docker y graphql-core. La misma base contiene tres usuarios y cuatro pedidos. El objetivo es construir una vista con **nombre, producto y total de los pedidos** para comparar contratos, viajes HTTP y acceso a datos.

## Empezar

Con Docker Desktop iniciado, desde la carpeta del proyecto:

```powershell
docker compose up -d --build --wait
docker compose exec -T api python demo.py all
```

La primera construcción necesita internet. No hace falta instalar Python en el host. El servidor publica únicamente `http://localhost:8000`; SQLite persiste en un volumen.

## Documentación

- [Tutorial breve de presentación](docs/TUTORIAL.md): dónde ir en el editor, código, explicación y comandos.
- [Tutorial en Word](docs/Tutorial-presentacion-demo.docx): versión DOCX del mismo manual.
- [Documento técnico](docs/CONCEPTOS.md): historia, problemas que resuelve cada enfoque, conceptos y límites de la comparación, con fuentes primarias.
- [Documento técnico en Word](docs/Conceptos-REST-GraphQL.docx).

## Un comando, un workflow completo

Los comandos se mantienen. Cada uno ahora tiene una función independiente en `workflows.py`; la salida muestra objetivo, solicitudes, resultado y costo.

| Comando | Función | Qué muestra |
| --- | --- | --- |
| `rest` | `demo_rest` | Usuarios y luego pedidos por usuario: under-fetching y campos sobrantes. |
| `overfetch` | `demo_overfetch` | Un GET agregado resuelve los viajes, pero trae datos de más. |
| `graphql` | `demo_graphql` | Campos elegidos por el cliente y pedidos cargados por lote. |
| `nplus1` | `demo_nplus1` | Misma query con una consulta SQL de pedidos por usuario. |
| `error` | `demo_error` | Campo inexistente rechazado por el esquema sin ejecutar SQL. |
| `all` | `demo_all` | Secuencia completa para ensayar. |

```powershell
docker compose exec -T api python demo.py rest
docker compose exec -T api python demo.py overfetch
docker compose exec -T api python demo.py graphql
docker compose exec -T api python demo.py nplus1
docker compose exec -T api python demo.py error
```

`-T` desactiva la terminal interactiva; el cliente no solicita entrada. Los textos largos se abrevian solo en pantalla. Para verlos completos:

```powershell
docker compose exec -T api python demo.py rest --full
```

`--base` después del subcomando cambia la URL del servidor. Ver ayuda:

```powershell
docker compose exec -T api python demo.py --help
docker compose exec -T api python demo.py graphql --help
```

## Cómo seguir el código

```text
demo.py (parser y handler)
  -> workflows.py (un recorrido completo por comando)
  -> demo_client.py (HTTP, impresión y métricas)
  -> app.py (recibir solicitud HTTP)
  -> routing.py (encontrar método + URL)
     -> rest_api.py (handler del recurso)
     -> graphql_api.py (validar query y ejecutar resolvers)
  -> database.py (Store y SQLite)
  -> respuesta JSON -> cliente -> resumen
```

| Archivo | Responsabilidad | Punto para mostrar |
| --- | --- | --- |
| `demo.py` | Parser y despacho | `build_parser`, `set_defaults(handler=...)`, `args.handler(args)` |
| `workflows.py` | Pasos de cada escenario | `demo_rest`, `demo_graphql`, `demo_nplus1` |
| `demo_client.py` | Transporte y métricas | `DemoClient.send`, `summary` |
| `app.py` | Servidor HTTP común | `handle_request` y conexión de las tablas de rutas |
| `routing.py` | Router pequeño sin framework | `Route`, `Router.dispatch` |
| `rest_api.py` | Endpoints REST independientes | `REST_ROUTES`, `list_users`, `list_user_orders`, `list_users_with_orders` |
| `graphql_api.py` | Contrato, resolvers y endpoint | `SCHEMA`, `create_schema`, `execute_query`, ambos `resolve_orders_*` |
| `database.py` | Base compartida y consultas medidas | `initialize`, `Store.select` |

El router usa una tabla explícita: cada entrada conecta un método y patrón de URL con una función. El bucle de registro del parser solo conecta comandos; no contiene su lógica. Los workflows comparten mecánica HTTP, pero mantienen visibles sus pasos. Los resolvers ingenuo y por lote son funciones separadas; se preparan dos esquemas idénticos para evitar modificar resolvers durante solicitudes concurrentes.

## Resultados esperados

| Escenario | HTTP | SELECT |
| --- | ---: | ---: |
| REST por recursos | 4 | 7 |
| REST agregado | 1 | 2 |
| GraphQL por lote | 1 | 2 |
| GraphQL ingenuo | 1 | 4 |

Las rutas de pedidos REST verifican primero al usuario, por eso cada una hace dos SELECT. La query compartida está en `workflows.py`:

```graphql
{ users { name orders { product total_cents } } }
```

`total_cents` expresa centavos. En GraphQL, `data` contiene los campos elegidos y `extensions` añade diagnóstico. `X-SQL-Queries` cuenta los SELECT de cada solicitud. Los bytes son cuerpos HTTP UTF-8, sin headers ni compresión, medidos antes de abreviar. En GraphQL incluyen el diagnóstico; no son un benchmark.

REST puede implementar selección de campos o endpoints específicos. GraphQL no optimiza SQL automáticamente: aquí usamos `SELECT *`. La carga por lote lee todos los pedidos y los agrupa; es suficiente para el dataset pequeño, pero un sistema grande necesita filtros y paginación. No usamos DataLoader. Su caché es por solicitud; N+1 también puede aparecer en REST.

## Presentar en cinco minutos

| Tiempo | Paso |
| --- | --- |
| 0:00 a 0:30 | Presentar la vista y la misma SQLite para ambos estilos. |
| 0:30 a 1:30 | `rest`: seguir `demo_rest` y la tabla `REST_ROUTES`. |
| 1:30 a 2:10 | `overfetch`: un GET y campos sobrantes. |
| 2:10 a 3:00 | `graphql`: mostrar esquema, query y selección de campos. |
| 3:00 a 4:15 | `nplus1`: comparar ambos resolvers y 4 frente a 2 SELECT. |
| 4:15 a 5:00 | Explicar cuándo elegir cada enfoque y sus costos. |

Construir y arrancar antes de comenzar. `error` es opcional; `all` sirve para ensayo. Tener una grabación de respaldo.

## Usar sin internet y llevar a la VM

En la misma máquina, con la imagen ya construida:

```powershell
docker compose up -d --no-build --pull never --wait
```

Para llevar a otra máquina, exportar previamente:

```powershell
docker save -o sdist-demo.tar sdist-grupo5-demo:1
```

Copiar `sdist-demo.tar` y `compose.yaml` a una carpeta de la VM. Docker y Compose deben estar instalados y el motor iniciado; la arquitectura de CPU debe ser compatible con la imagen. Desde esa carpeta:

```powershell
docker load -i sdist-demo.tar
docker compose up -d --no-build --pull never --wait
docker compose exec -T api python demo.py all
```

Los comandos Docker también sirven en la terminal Linux. El servidor y el cliente no requieren servicios externos durante la ejecución.

## Operación y diagnóstico

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health
docker compose logs --tail 30 api
docker compose restart api
docker compose down
```

`down` detiene el servicio y conserva SQLite. Solo para borrar los datos de prueba y recrearlos al arrancar:

```powershell
docker compose down -v
docker compose up -d --no-build --pull never --wait
```

Si el código cambió, reconstruir con `docker compose up -d --build --wait`; `restart` no incorpora cambios de archivos. Si no conecta al motor, iniciar Docker Desktop. Si el puerto 8000 está ocupado, liberar el puerto o cambiar el puerto del host en `compose.yaml`. El cliente dentro del contenedor sigue usando el 8000 interno.

## Endpoints y consultas manuales en PowerShell

| Método | Ruta | Resultado |
| --- | --- | --- |
| GET | `/health` | Proceso disponible |
| GET | `/api/v1/users` | Usuarios sin pedidos |
| GET | `/api/v1/users/1` | Usuario individual; 404 si no existe |
| GET | `/api/v1/users/1/orders` | Pedidos del usuario |
| GET | `/api/v1/users-with-orders` | Usuarios con pedidos completos |
| POST | `/graphql` | Query GraphQL |

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/users | ConvertTo-Json -Depth 10

$body = @{ query = '{ users { name orders { product total_cents } } }' } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/graphql -Method Post -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri http://localhost:8000/graphql -Method Post -ContentType 'application/json' -Headers @{ 'X-Resolver-Mode' = 'naive' } -Body $body | ConvertTo-Json -Depth 10
```

GraphQL acepta `query`, `variables` y `operationName`. El header didáctico `X-Resolver-Mode` selecciona `naive` o `batched` (predeterminado). JSON inválido produce 400; campos GraphQL inválidos generan `errors` con HTTP 200 en esta implementación. Solo hay lecturas: no se implementan POST REST, PUT, DELETE ni mutations.

## Desarrollo y documentación

En PowerShell con Python 3.13 instalado:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe app.py
```

En otra terminal:

```powershell
.\.venv\Scripts\python.exe demo.py all
```

Sin Docker, SQLite se guarda en `data/demo.sqlite`; `DB_PATH` permite cambiar la ubicación. Para regenerar los dos documentos Word desde los Markdown, sin instalar bibliotecas adicionales:

```powershell
.\.venv\Scripts\python.exe tools/build_docs.py
```

Cerrar los DOCX en Word antes de regenerarlos. La generación no necesita internet. El servidor es didáctico para localhost: no implementa autenticación, autorización ni límites de complejidad GraphQL. La caché HTTP está desactivada (`no-store`); no se compara caché en esta demo.
