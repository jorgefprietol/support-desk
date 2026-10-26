# Flujo de operación

![Flujo de operación](diagrams/flow.svg)

[Abrir SVG](diagrams/flow.svg) · [Fuente Mermaid](diagrams/flow.mmd)


<details>
<summary>Versión Mermaid</summary>

```mermaid
flowchart TD
    Start["Recibir mensaje y conversación"] --> Auth["Validar token, clave y datos"]
    Auth --> Replay{"¿Solicitud ya completada?"}
    Replay -->|Sí| Previous["Devolver respuesta persistida"]
    Replay -->|No| State["Cargar estado de conversación"]
    State --> Handoff{"¿Escalada o atención solicitada?"}
    Handoff -->|Sí| Queue["Mantener o crear cola humana"]
    Handoff -->|No| Search["Filtrar organización y buscar políticas"]
    Search --> Evidence{"¿Existe una fuente válida?"}
    Evidence -->|Sí| Answer["Responder con fragmento y versión"]
    Evidence -->|No| Queue
    Answer --> Save["Persistir turnos y auditoría"]
    Queue --> Save
    Save --> Operator["Resolver por operación explícita"]
```

</details>

- `message` conserva el canal de la conversación y rechaza continuar una conversación cerrada.
- `ask_human` no depende de disponibilidad del modelo; una conversación escalada sigue pendiente hasta `resolve`.
- Una respuesta citada mantiene el estado abierto: no demuestra por sí misma resolución del cliente.

Las operaciones del dominio se guardan junto a auditoría y respuesta idempotente en la transacción del servicio local. Un error revierte los cambios de esa solicitud.

[Arquitectura](architecture.md) · [Tecnologías y alcance](technologies.md)
