"""A channel-neutral support inbox with evidence and human handoff."""
import re
import time
from app.retrieval import answer, identifier, initialize, put, remove, search

TITLE = "Support Desk"
DESCRIPTION = "Atención con respuestas documentadas, conversaciones y escalamiento humano."
DEMO = {"action": "demo", "tenant": "demo-shop", "conversation_id": "conversation-demo", "message": "devolución producto plazo"}
FAQS = [
    {"id": "returns", "title": "Devolución de productos", "text": "La devolución de un producto puede solicitarse dentro de treinta días desde la entrega. El producto debe conservar su embalaje y comprobante. El equipo de soporte valida cada solicitud antes de emitir el reembolso."},
    {"id": "shipping", "title": "Entrega y seguimiento", "text": "El plazo de entrega es de tres a cinco días hábiles. El seguimiento del envío está disponible con el número de pedido en el portal de clientes. Los retrasos de entrega se revisan con soporte."},
    {"id": "billing", "title": "Facturación y comprobantes", "text": "La factura se envía al correo registrado después de confirmar el pago. Las correcciones de facturación requieren número de pedido y comprobante de pago."},
]


def _initialize(connection):
    initialize(connection)
    connection.execute("CREATE TABLE IF NOT EXISTS conversations (tenant TEXT, conversation_id TEXT, channel TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL, escalated_at REAL, resolved_at REAL, resolution TEXT, PRIMARY KEY(tenant,conversation_id))")
    connection.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL, conversation_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at REAL NOT NULL)")


def _redact(text):
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[correo]", text)
    return re.sub(r"(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)", "[teléfono]", text)


def _read(connection, tenant, conversation_id):
    row = connection.execute("SELECT * FROM conversations WHERE tenant=? AND conversation_id=?", (tenant, conversation_id)).fetchone()
    if row is None:
        raise ValueError("conversation not found")
    result = dict(row)
    result["messages"] = [dict(message) for message in connection.execute("SELECT role,content,created_at FROM messages WHERE tenant=? AND conversation_id=? ORDER BY id", (tenant, conversation_id))]
    result["resolution_seconds"] = round(row["resolved_at"] - row["escalated_at"], 3) if row["resolved_at"] is not None and row["escalated_at"] is not None else None
    return result


def process(payload, store):
    connection = store.connection
    _initialize(connection)
    tenant = identifier(payload.get("tenant"), "tenant")
    action = payload.get("action", "message")
    if action == "demo":
        for faq in FAQS:
            put(connection, tenant, faq)
        action = "message"
    if action == "knowledge_upsert":
        result = put(connection, tenant, payload.get("document"))
        store.event("support.knowledge_updated", {"tenant": tenant, "document_id": result["document_id"], "version": result["version"]})
        return result
    if action == "knowledge_delete":
        return {"deleted": remove(connection, tenant, payload.get("document_id"))}
    if action == "metrics":
        counts = {row["status"]: row["count"] for row in connection.execute("SELECT status,count(*) AS count FROM conversations WHERE tenant=? GROUP BY status", (tenant,))}
        mean = connection.execute("SELECT avg(resolved_at-escalated_at) FROM conversations WHERE tenant=? AND resolved_at IS NOT NULL", (tenant,)).fetchone()[0]
        return {"tenant": tenant, "open_conversations": counts.get("open", 0), "pending_human": counts.get("escalated", 0), "resolved_by_human": counts.get("resolved", 0), "human_resolution_mean_seconds": round(mean, 3) if mean is not None else None, "measurement": "Persisted local conversation states; a documented answer does not establish customer resolution"}
    conversation_id = identifier(payload.get("conversation_id"), "conversation_id")
    if action == "conversation":
        return _read(connection, tenant, conversation_id)
    if action == "resolve":
        operator = identifier(payload.get("operator"), "operator")
        resolution = payload.get("resolution")
        if not isinstance(resolution, str) or not resolution.strip() or len(resolution) > 2000:
            raise ValueError("resolution is required (up to 2000 characters)")
        row = _read(connection, tenant, conversation_id)
        if row["status"] != "escalated":
            raise ValueError("only escalated conversations may be resolved")
        connection.execute("UPDATE conversations SET status='resolved',resolution=?,resolved_at=? WHERE tenant=? AND conversation_id=?", (_redact(resolution), time.time(), tenant, conversation_id))
        store.event("support.resolved", {"tenant": tenant, "conversation_id": conversation_id, "operator": operator})
        return _read(connection, tenant, conversation_id)
    if action != "message":
        raise ValueError("unknown action")
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip() or len(message) > 2000:
        raise ValueError("message is required (up to 2000 characters)")
    channel = payload.get("channel", "web")
    if channel not in {"web", "email", "whatsapp"}:
        raise ValueError("unsupported channel")
    if "ask_human" in payload and not isinstance(payload["ask_human"], bool):
        raise ValueError("ask_human must be a boolean")
    now = time.time()
    row = connection.execute("SELECT status,channel FROM conversations WHERE tenant=? AND conversation_id=?", (tenant, conversation_id)).fetchone()
    if row and row["status"] == "resolved":
        raise ValueError("conversation closed; use a new conversation_id")
    if row and row["channel"] != channel:
        raise ValueError("conversation channel cannot change")
    connection.execute("INSERT OR IGNORE INTO conversations VALUES(?,?,?,'open',?,NULL,NULL,NULL)", (tenant, conversation_id, channel, now))
    connection.execute("INSERT INTO messages(tenant,conversation_id,role,content,created_at) VALUES(?,?,'customer',?,?)", (tenant, conversation_id, _redact(message), now))
    if row and row["status"] == "escalated":
        return {"conversation_id": conversation_id, "status": "escalated", "answer": "Tu consulta está pendiente de atención del equipo.", "sources": [], "resolution": "pending-human"}
    if payload.get("ask_human", False):
        # A human handoff must remain available when the model is unavailable.
        result = {"answer": "El equipo de soporte revisará tu consulta.", "sources": [], "abstained": True, "method": "explicit-handoff"}
    else:
        result = answer(message, search(connection, tenant, message, []))
    escalated = payload.get("ask_human", False) or result["abstained"]
    if escalated:
        connection.execute("UPDATE conversations SET status='escalated',escalated_at=? WHERE tenant=? AND conversation_id=?", (now, tenant, conversation_id))
        result.update({"answer": "El equipo de soporte revisará tu consulta.", "sources": [], "abstained": True})
    connection.execute("INSERT INTO messages(tenant,conversation_id,role,content,created_at) VALUES(?,?,'support',?,?)", (tenant, conversation_id, result["answer"], now))
    store.event("support.responded", {"tenant": tenant, "conversation_id": conversation_id, "escalated": escalated, "source_count": len(result["sources"])})
    return {**result, "conversation_id": conversation_id, "status": "escalated" if escalated else "open", "resolution": "pending-human" if escalated else "documented-answer"}
