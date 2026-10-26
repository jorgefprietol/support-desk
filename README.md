# Support Desk

Bandeja de atención con respuestas apoyadas en políticas, historial de conversación y escalamiento humano. Una consulta sobre devoluciones recibe el fragmento vigente de la política; una consulta sin evidencia pasa a la cola del equipo. Las conversaciones escaladas permanecen en esa cola hasta su resolución explícita.

El servicio funciona localmente con Python y SQLite. Incluye búsqueda TF-IDF y un selector de fuentes opcional con Ollama. El canal de entrada puede etiquetarse como web, correo o WhatsApp; no se realizan envíos a esas plataformas.

## Ejecutar

Requiere Python 3.10 o superior. Desde el repositorio:

```powershell
python -m app demo
python -m unittest discover -s tests -v
$env:SERVICE_TOKEN = [guid]::NewGuid().ToString('N')
python -m app serve
```

Abrir `http://127.0.0.1:8080` e introducir el token configurado. La demo usa datos ficticios y una base temporal. El servidor conserva conversaciones en `var/service.db`.

Para ejecutar una secuencia persistente:

```powershell
python -m app run --input data/demo.json --key support-demo-1
python -m app run --input data/escalation.json --key escalation-1
python -m app run --input data/resolution.json --key resolution-1
python -m app run --input data/metrics.json --key metrics-1
```

## Contrato

`POST /api/run` requiere un token Bearer y `Idempotency-Key`, además del cuerpo JSON. Una clave identifica una operación; repetirla con otro cuerpo devuelve conflicto. Cada conversación pertenece a una organización y a un canal inmutable.

| Acción | Campos | Comportamiento |
| --- | --- | --- |
| `message` | `tenant`, `conversation_id`, `message`, `channel`, `ask_human` opcional | Responde con fuente o escala |
| `conversation` | `tenant`, `conversation_id` | Recupera estado e historial |
| `resolve` | `tenant`, `conversation_id`, `operator`, `resolution` | Cierra una conversación escalada |
| `knowledge_upsert` | `tenant`, `document`: `id`, `title`, `text`, `expected_version` opcional | Publica una política versionada |
| `knowledge_delete` | `tenant`, `document_id` | Retira la política |
| `metrics` | `tenant` | Estados y tiempo medio de resolución humana |
| `demo` | `tenant`, `conversation_id`, `message` | Carga políticas ficticias y atiende |

Los correos y teléfonos reconocibles se ocultan antes de persistir el mensaje. Esto reduce exposición de datos comunes, sin constituir una anonimización completa.

## Medición y alcance

Las métricas de dominio cuentan conversaciones abiertas, pendientes y cerradas por una persona; el tiempo de resolución se mide desde el escalamiento hasta el cierre. Una respuesta documentada no demuestra que el cliente haya resuelto su problema. `/api/metrics` mide transacciones únicas completadas y sus latencias locales.

El token autentica al integrador. La separación entre usuarios, organizaciones y operadores requiere que el adaptador derive `tenant` y permisos de una identidad verificada. Las acciones administrativas no deben exponerse directamente al cliente final. Los campos `operator` y `channel` son metadatos, no mecanismos de autenticación.

La integración WhatsApp requeriría verificar la firma del webhook, normalizar eventos, deduplicarlos con su identificador y enviar mensajes con credenciales propias. Ese conector no está habilitado. La búsqueda local es lexical y de pequeña escala; la conexión Ollama requiere un servidor y un modelo, sin asumir disponibilidad externa.

Consulta [arquitectura](docs/architecture.md), [decisiones](docs/decisions.md), [operación](docs/operations.md) y [referencias](docs/references.md).
