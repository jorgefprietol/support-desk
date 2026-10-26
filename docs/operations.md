# Operación

La retirada de una política afecta a consultas nuevas. Los mensajes de soporte y las respuestas guardadas para idempotencia pueden conservar extractos anteriores; la retención debe abarcar conversaciones, `requests`, copias de seguridad y exportaciones. El escalamiento explícito con `ask_human=true` evita la dependencia del modelo.

Ejecutar pruebas y demo antes de iniciar una sesión persistente. Las políticas del ejemplo son ficticias: reemplazarlas por contenido aprobado mediante `knowledge_upsert` antes de atender consultas reales.

Usar `SERVICE_TOKEN` de al menos 24 caracteres. El servidor escucha en loopback por defecto. La API de servicio está dirigida a un integrador de confianza; proteger las operaciones de edición de políticas y resolución con una autorización de operador en el adaptador. No utilizar el campo `operator` como prueba de identidad.

El modo local no hace llamadas de red. Para seleccionar fuentes con un modelo, configurar `MODEL_BACKEND=ollama`, `OLLAMA_URL` y `OLLAMA_MODEL` según `.env.example`. El modelo debe estar disponible antes de ejecutar. Un fallo externo revierte la petición; reintentar con la misma clave permite conservar la semántica de la operación.

Cada entrega del canal debe usar su identificador estable como `Idempotency-Key`. Mantener la misma organización y conversación para los turnos de un hilo. No reutilizar una clave para mensajes distintos. Una conversación cerrada no se reabre automáticamente.

Consultar la acción `metrics` para pendientes y tiempos de atención. El denominador de resolución humana solo incluye conversaciones cerradas; vigilar también el volumen pendiente para evitar una lectura sesgada de la media. El host ofrece métricas de latencia local separadas.

`var/service.db` contiene conversaciones y respuestas. Definir retención y eliminación de datos antes de usar información real. La ocultación de teléfonos y correos no detecta toda la información personal. Detener el servicio antes de copiar la base o usar backup transaccional de SQLite.

Para WhatsApp u otro proveedor: validar firma y tipo de evento, obtener la identidad del canal, normalizar al contrato interno, fijar organización y permisos, y enviar la respuesta mediante el SDK oficial. Probar duplicados, reintentos y cambios de conversación. Estos pasos no forman parte de la demo local.
