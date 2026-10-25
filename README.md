# Grupo 5: REST y GraphQL

Demo de terminal con Python 3.13, SQLite y un esquema GraphQL real (graphql-core).
Ambas APIs consultan la misma base: tres usuarios y cuatro pedidos ficticios.
Objetivo del cliente: mostrar **nombre de cada usuario, producto y total de sus pedidos**.
Los importes son enteros en centavos, para evitar errores de punto flotante.

## Preparar con internet (antes de la clase)

Instalar Docker con Compose y arrancar su motor (Docker Desktop en Windows).
En la carpeta del proyecto:

```sh
docker compose build
docker compose up -d --wait
docker compose exec api python demo.py all
```

Solo la construccion descarga la imagen base y las dependencias. El servidor y el
cliente no usan servicios externos. No se necesita Python ni curl en el host.
El puerto se publica solo en `127.0.0.1:8000`; no queda expuesto a la red de la VM.

## Ejecutar sin internet

Si ya se construyo la imagen en esa maquina:

```sh
docker compose up -d --no-build --pull never --wait
docker compose exec api python demo.py rest
docker compose exec api python demo.py overfetch
docker compose exec api python demo.py graphql
docker compose exec api python demo.py nplus1
```

Si se lleva a otra maquina, exportar **antes** con internet:

```sh
docker save -o sdist-demo.tar sdist-grupo5-demo:1
```

Copiar `sdist-demo.tar` y `compose.yaml` a la VM (misma arquitectura de CPU que la
maquina que construyo la imagen). Docker y Compose deben estar instalados previamente.
En la VM, sin internet:

```sh
docker load -i sdist-demo.tar
docker compose up -d --no-build --pull never --wait
docker compose exec api python demo.py all
```

El cliente esta incluido en la imagen. SQLite se crea automaticamente en el primer
arranque y persiste en un volumen. `docker compose down` detiene la demo y conserva
los datos. `docker compose down -v` elimina el volumen: usarlo solo para reiniciar
los datos de prueba, que se recrean en el siguiente arranque.

## Guion de hasta cinco minutos

Dejar el contenedor listo **antes** de empezar. Ejecutar cada comando por separado
y explicar el resultado. Las respuestas muestran campos extra deliberadamente;
las biografias largas hacen visible el costo del over-fetching.

| Tiempo | Comando (despues de `docker compose exec api python demo.py`) | Que explicar |
| --- | --- | --- |
| 0:00–0:30 | — | Misma SQLite, dos contratos. Solo necesitamos nombre, producto y total. |
| 0:30–1:30 | `rest` | GET de usuarios no incluye pedidos: under-fetching. Se requieren otros tres GET. Ademas llegan campos sobrantes. |
| 1:30–2:10 | `overfetch` | Endpoint agregado: un GET, pero devuelve mas campos de los necesarios. |
| 2:10–3:00 | `graphql` | Una query pide exactamente los campos de la vista. Dos SELECT con carga por lote. |
| 3:00–4:15 | `nplus1` | Misma query y mismos datos: un request HTTP, pero 1 + 3 SELECT por resolvers ingenuos. Comparar con los dos SELECT anteriores. |
| 4:15–5:00 | — | Elegir segun clientes y contratos. REST admite endpoints especificos y seleccion de campos; GraphQL exige cuidar resolvers y costo de consultas. |

Opcional fuera del guion: `docker compose exec api python demo.py error` pide un campo
inexistente. El esquema lo rechaza antes de ejecutar SQL; revisar `errors` incluso con HTTP 200.
No hace falta mostrar este caso para cumplir el trade-off: N+1 ya lo demuestra.

## Resultados y limites de la comparacion

| Escenario | HTTP | SELECT con estos datos |
| --- | ---: | ---: |
| REST por recursos | 4 | 7 |
| REST agregado | 1 | 2 |
| GraphQL por lote | 1 | 2 |
| GraphQL ingenuo | 1 | 4 |

REST por recursos verifica la existencia del usuario antes de consultar sus pedidos,
por eso cada ruta de pedidos hace dos SELECT. No confundir requests HTTP con consultas SQL.
`X-SQL-Queries` cuenta SELECT de esa solicitud; GraphQL incluye tambien el SQL en
`extensions` con fines didacticos.

Los bytes son los cuerpos HTTP UTF-8 reales, sin headers ni compresion. En GraphQL
incluyen `extensions` de diagnostico, que no son datos solicitados por el cliente.
No son una prueba de rendimiento: el dataset y las biografias son ilustrativos.
GraphQL selecciona campos en la respuesta, pero esta implementacion lee filas
completas de SQLite. La carga por lote lee todos los pedidos, adecuada solo para
este dataset; en un sistema grande se filtraria por IDs y se agregaria paginacion.

La demo desactiva cache con `Cache-Control: no-store` para repetir mediciones. REST
permite aprovechar cache HTTP por URL; GraphQL puede usar caches de cliente,
consultas persistidas y otras estrategias. Aqui no se implementa una comparacion de cache.
El N+1 depende del acceso a datos: tambien puede aparecer en REST.

## Contratos y endpoints

- `GET /health`: estado del proceso.
- `GET /api/v1/users`: usuarios completos sin pedidos.
- `GET /api/v1/users/1`: usuario individual (404 si no existe).
- `GET /api/v1/users/1/orders`: pedidos del usuario.
- `GET /api/v1/users-with-orders`: usuarios con pedidos completos.
- `POST /graphql`: JSON con `query`, opcionalmente `variables` y `operationName`.
- Header GraphQL `X-Resolver-Mode: naive` o `batched` (predeterminado).

Ejemplo con curl en Linux/macOS (en PowerShell puede usarse el cliente Python):

```sh
curl -i http://localhost:8000/api/v1/users/999
curl -i http://localhost:8000/graphql -H 'Content-Type: application/json' --data '{"query":"{ users { name orders { product total_cents } } }"}'
```

Solo se implementan lecturas: POST en GraphQL transporta una query, no crea un recurso.
GET/POST/PUT/DELETE, versionado y contratos se explican en el teorico. `/api/v1`
ilustra versionado REST; en GraphQL se puede evolucionar el esquema agregando campos
y deprecando los anteriores, manteniendo compatibilidad. Eso requiere criterio en ambos estilos.
Servidor didactico para localhost, sin autenticacion ni limites de costo GraphQL.

## Desarrollo sin Docker

Con Python 3.13:

```sh
python -m venv .venv
```

Activar el entorno (`.venv/Scripts/Activate.ps1` en PowerShell o
`source .venv/bin/activate` en Linux), y luego:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py
```

En otra terminal: `python demo.py all`. La instalacion necesita internet una vez;
la ejecucion no. `DB_PATH` permite cambiar el archivo (por defecto `data/demo.sqlite`).

Referencias: [resolvers de graphql-core](https://graphql-core-3.readthedocs.io/en/stable/usage/resolvers.html)
y [SQLite en Python](https://docs.python.org/3.13/library/sqlite3.html).
