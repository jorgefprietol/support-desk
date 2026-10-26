# Tecnologías y alcance

Python 3.10+, SQLite y recuperación TF-IDF; selector de fuentes con Ollama opcional. Incluye consola HTTP, contenedor y workflow de entrada n8n.

| Tecnología | Estado | Uso en este proyecto |
| --- | --- | --- |
| Python 3.10+ y biblioteca estándar | Implementado | Dominio, API HTTP, validación y CLI. |
| SQLite / sqlite3 | Implementado | Conversaciones, mensajes, políticas, versiones, auditoría e idempotencia. |
| TF-IDF, coseno y filtro SQL | Implementado | Ranking lexical después de filtrar la organización; salida extractiva con cita. |
| Ollama / HTTP JSON | Opcional | Selecciona una fuente recuperada; necesita servidor y modelo configurados. |
| n8n | Workflow incluido | Webhook autenticado hacia la API; requiere importación y credenciales. |
| Docker / Compose | Archivos incluidos | Servicio local y perfil de orquestación; ejecución del contenedor no acreditada por las pruebas unitarias. |
| unittest / GitHub Actions | Implementado | Pruebas de dominio y HTTP en Python 3.10 y 3.12. |
| WhatsApp, correo y proveedor de identidad | Por conectar | Firma de eventos, envío de respuestas e identidad de usuarios no implementados. |

“Implementado” describe código disponible y comprobable en el repositorio. “Opcional” requiere un proveedor configurado; “incluido” identifica un archivo o adaptador entregado, sin afirmar una integración externa ejecutada.

[Arquitectura](architecture.md) · [Flujo de operación](flow.md) · [Integraciones](integrations.md)
