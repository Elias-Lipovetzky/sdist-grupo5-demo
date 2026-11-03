# REST y GraphQL: contexto y conceptos de la demo

Documento de apoyo para comprender y explicar las decisiones. La guía de presentación está en [TUTORIAL.md](TUTORIAL.md). Aquí se distingue el concepto general de lo que implementa este proyecto.

## 1. El problema: comunicar procesos con un contrato

Una API permite que un programa solicite operaciones o datos a otro mediante un contrato. En un sistema distribuido el cliente y el servidor pueden estar en máquinas distintas: cada viaje de red tiene costo y puede fallar. Por eso importa cuántas solicitudes hacen falta, qué información se transfiere y cuánto trabajo realiza el servidor.

La demo ejecuta procesos de cliente y servidor dentro de un contenedor y los comunica por HTTP en localhost. No pretende simular una infraestructura distribuida completa: aísla las decisiones del contrato y del acceso a datos para observarlas con facilidad. SQLite es almacenamiento local, no una base distribuida.

La pregunta concreta es cómo construir una vista con nombre de usuario, producto y total de sus pedidos. Tener el mismo dataset en ambos estilos evita atribuir diferencias a los datos.

## 2. De la Web a REST

Roy Fielding formalizó REST en su tesis doctoral de 2000 para describir principios arquitectónicos de la Web. No fue una biblioteca creada para sustituir GraphQL ni un formato sinónimo de JSON. Su contexto es cómo mantener una Web extensible, escalable y con componentes que puedan evolucionar de forma independiente. [Tesis de Fielding](https://ics.uci.edu/~fielding/pubs/dissertation/top.htm).

REST propone restricciones como separación cliente-servidor, interacción sin estado de sesión almacenado entre solicitudes, cacheabilidad, interfaz uniforme y capas; el código bajo demanda es opcional. Un recurso se identifica y se intercambian representaciones de su estado. La interfaz uniforme también incluye mensajes autodescriptivos e hipermedia para guiar interacciones. Tener rutas con sustantivos y JSON no basta por sí solo para cumplir todas esas restricciones. [Capítulo sobre REST](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm).

Nuestra API ilustra recursos, métodos, estados y respuestas definidas por el servidor. No implementa navegación mediante hipermedia ni todas las restricciones de una API REST completa. “REST” en el guion se refiere a esa comparación didáctica de recursos HTTP.

## 3. HTTP: métodos y estados

HTTP aporta semántica común. GET recupera una representación; POST solicita procesamiento según el recurso; PUT crea o reemplaza su estado en una URI conocida; DELETE solicita eliminar la asociación del recurso con esa URI. GET es seguro; PUT y DELETE son idempotentes: repetir la operación tiene el mismo efecto pretendido, aunque pueda cambiar la respuesta. Entre los estados están 200 (éxito), 201 (creado), 204 (éxito sin contenido), 400 (solicitud inválida), 404 (no encontrado) y 500 (error del servidor). [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html).

En este proyecto solo hay lecturas. `GET /api/v1/users` devuelve usuarios; `GET /api/v1/users/1/orders` devuelve pedidos de un usuario. `POST /graphql` transporta una query: el método POST no implica que esta operación esté creando datos. Una ruta o un usuario inexistentes producen 404; un cuerpo JSON inválido produce 400. La demo devuelve HTTP 200 para resultados GraphQL con errores de validación: el cliente debe revisar `errors`. Esa es una decisión del transporte implementado, no una regla universal para todo servidor GraphQL.

## 4. Over-fetching y under-fetching

Son problemas relativos a la necesidad de un cliente, no propiedades inevitables de un protocolo. Over-fetching significa recibir más datos de los necesarios; under-fetching, que una respuesta no contiene toda la información para completar la tarea.

En `demo_rest`, el GET de usuarios contiene email, domicilio y biografía sobrantes para la vista, pero no contiene pedidos. El cliente debe hacer tres GET adicionales. En `demo_overfetch`, un endpoint agregado resuelve los viajes en un GET, pero mantiene los campos sobrantes.

Se podrían diseñar endpoints REST específicos, parámetros de selección de campos o expansiones de relaciones. Cada opción cambia el contrato y su mantenimiento. La demo compara unos endpoints concretos con una query GraphQL, no demuestra que REST siempre necesite más solicitudes o bytes.

## 5. Por qué surge GraphQL

GraphQL comenzó en Facebook en 2012 durante la reconstrucción de sus aplicaciones móviles nativas. Necesitaban obtener datos del News Feed con una estructura cercana a los objetos que consumía la interfaz. La distancia entre esos datos y las consultas disponibles impulsó el proyecto. En 2015 se inició su apertura mediante especificación y una implementación de referencia. [Anuncio original, septiembre de 2015](https://graphql.org/blog/2015-09-14-graphql/).

Ese origen ayuda a entender su propuesta: dar al cliente una forma de expresar qué partes de un grafo de datos necesita. No vuelve obsoleto a REST ni elimina el trabajo de diseñar contratos y acceder eficientemente a los datos.

## 6. Esquema, query y resolver

El esquema es el contrato tipado: describe campos, relaciones y argumentos disponibles. En `server/graphql_api.py`, `Query.users` devuelve `[User!]!`: una lista no nula de usuarios no nulos. Un `User` tiene `orders`, que relaciona usuarios con pedidos. El esquema público no tiene por qué copiar las tablas internas. GraphQL tampoco requiere una base de datos de grafos. [Esquemas y tipos](https://graphql.org/learn/schema/).

Una query selecciona campos dentro de ese contrato. Puede anidar relaciones, usar argumentos, variables y aliases. Las operaciones principales son query (lectura), mutation (cambio) y subscription (actualizaciones); esta demo implementa queries únicamente. [Queries](https://graphql.org/learn/queries/).

```graphql
{ users { name orders { product total_cents } } }
```

En el proyecto, `execute_query` valida el cuerpo HTTP y llama a `graphql_sync`. La biblioteca analiza y valida el documento y ejecuta los resolvers. `resolve_users` obtiene usuarios; el resolver de `User.orders` obtiene pedidos. El acceso a la base está en `server/database.py`. Los campos simples de los diccionarios se resuelven mediante el comportamiento predeterminado de la biblioteca.

Seleccionar campos de respuesta no significa seleccionar automáticamente columnas SQL: nuestro repositorio usa `SELECT *`. Además, el esquema tipado no reemplaza la autorización. Permitir pedir un campo y permitir verlo a un usuario son decisiones distintas.

## 7. N+1 y carga por lote

N+1 ocurre cuando una consulta inicial obtiene N objetos y después se consulta una relación por cada objeto. En esta demo, `resolve_orders_naive` produce un SELECT de usuarios más tres SELECT de pedidos. Aumentar los usuarios aumenta las consultas, aunque el cliente siga enviando un solo POST.

`resolve_orders_batched` hace una carga de pedidos, los agrupa por `user_id` y reutiliza esos grupos durante la solicitud. El costo queda en dos SELECT para la query de ejemplo. Ambas estrategias usan contratos idénticos y se eligen con el header didáctico `X-Resolver-Mode`, de modo que la comparación cambia solo la ejecución del backend.

DataLoader es una herramienta conocida para agrupar accesos y memorizar resultados; normalmente se crean instancias por solicitud para no mezclar datos o permisos entre usuarios. La demo ilustra el principio, pero no usa esa biblioteca: carga todos los pedidos sin una cola de claves ni su API. N+1 no es exclusivo de GraphQL; también puede surgir en handlers REST u ORM. [DataLoader](https://github.com/graphql/dataloader).

La carga por lote actual sirve para cuatro pedidos. En un sistema grande convendría consultar por IDs necesarios y paginar. Bajar el número de SELECT no basta: también importan filas leídas, índices, memoria y latencia.

## 8. Contratos, versionado y caché

`/api/v1` muestra una versión explícita en la URI. Para este proyecto, un cambio incompatible podría motivar otra versión, aunque no es la única estrategia de evolución REST. GraphQL permite agregar campos y deprecar otros sin cambiar inmediatamente a los clientes. Eliminar campos, cambiar tipos o restringir valores puede romper consumidores: tener un solo endpoint no elimina ese riesgo. La documentación oficial trata la evolución del esquema y la caché como decisiones de diseño adicionales. [Buenas prácticas GraphQL](https://graphql.org/learn/best-practices/).

La demo envía `Cache-Control: no-store` para observar solicitudes reales repetidas. No mide caché. En una solución real, se puede diseñar caché HTTP para representaciones REST y estrategias para GraphQL, como caché normalizada del cliente o consultas persistidas. Aquí `orders_cache` solo evita releer pedidos en un mismo request; no conserva resultados entre requests.

## 9. Cómo leer las mediciones

| Escenario | Solicitudes HTTP | SELECT | Cuerpos recibidos con datos iniciales |
| --- | ---: | ---: | ---: |
| REST por recursos | 4 | 7 | 1662 bytes |
| REST agregado | 1 | 2 | 1692 bytes |
| GraphQL por lote | 1 | 2 | 413 bytes |
| GraphQL ingenuo | 1 | 4 | 535 bytes |

Los siete SELECT de REST incluyen verificar cada usuario antes de consultar sus pedidos. Es una decisión de este código. `Store.select` registra las consultas y `X-SQL-Queries` las comunica al cliente. Los bytes son cuerpos HTTP UTF-8, sin headers ni compresión; en GraphQL incluyen SQL y diagnóstico de `extensions`. La diferencia de bytes entre las dos estrategias GraphQL se debe al diagnóstico, no a que cambien los datos de la vista.

La salida abrevia textos largos solo al imprimirlos. Mide bytes antes de hacerlo; `--full` muestra el cuerpo completo. Las biografías deliberadamente extensas hacen visible el over-fetching, por lo que estas cifras no constituyen un benchmark general.

## 10. La arquitectura elegida para explicarlo

El parser de `client/cli.py` asocia cada subcomando con una función usando `set_defaults(handler=...)`. `args.handler(args)` ejecuta el workflow. En `client/workflows.py`, cada función conserva el recorrido completo del escenario, mientras `client/demo_client.py` comparte únicamente HTTP, impresión y métricas.

El servidor recibe HTTP en `server/http_server.py` y usa la tabla de `server/routing.py`. Los handlers REST están en `server/rest_api.py`; GraphQL reúne esquema, resolvers y ejecución en `server/graphql_api.py`. Ambos acceden al mismo `Store` de `server/database.py`. Esta separación permite seguir un comando hasta SQLite sin mezclar decisiones de presentación, transporte y datos.

Se mantuvo un router pequeño en lugar de agregar un framework para que la tabla de entradas y los handlers fueran visibles. Docker empaqueta el entorno; la imagen se construye con internet una vez y luego puede cargarse en una VM compatible sin conexión. No se agregaron autenticación, paginación ni límites de complejidad; el servidor es didáctico para localhost.

Como criterio de elección para este caso: endpoints estables y sencillos favorecen una API por recursos; pantallas variadas que combinan relaciones pueden beneficiarse de selección GraphQL. En ambos hay que medir acceso a datos, diseñar compatibilidad y aplicar permisos. Son decisiones del sistema, no una competencia con un ganador universal.
