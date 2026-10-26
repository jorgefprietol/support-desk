# Decisiones

| Decisión | Motivo | Consecuencia |
| --- | --- | --- |
| Contrato neutral respecto del canal | Mantiene la lógica independiente de proveedores | El adaptador debe validar el webhook real |
| Cola humana persistente | Evita respuestas automáticas mientras hay una intervención pendiente | El operador debe cerrar expresamente |
| Citas con versión | Permite revisar qué política respaldó la respuesta | Los cambios requieren publicar una nueva versión |
| Fragmentos en lugar de respuestas libres | Reduce afirmaciones no respaldadas | La conversación tiene menos flexibilidad lingüística |
| Ocultar correos y teléfonos al persistir | Reduce datos de contacto innecesarios | Otros datos personales todavía requieren tratamiento |
| Canal inmutable por conversación | Evita mezclar identidades de canales distintos | Un cambio de canal requiere otra conversación |

Las ideas de atención con recuperación y orquestación se estudiaron en las referencias. Los estados, reglas de persistencia y tests de este servicio se definieron para su alcance local.
