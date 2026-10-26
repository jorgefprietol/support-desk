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

Las versiones se conservan en un registro por organización y documento. El borrado elimina texto y fragmentos del índice, pero avanza una revisión de baja; recrear el mismo identificador continúa la secuencia. Por ejemplo, versión 1, baja 2 y nueva publicación 3. Así, `expected_version` anterior a la baja no permite restaurar ni sobrescribir una política nueva. El registro conserva sólo identificadores y revisión; repetir una baja ausente no consume otra revisión. Los identificadores de fragmento siguen estables por posición y se interpretan junto a su versión.
