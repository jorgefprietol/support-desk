import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app.domain import DEMO, FAQS, process
from app.runtime import Store


class SupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "support.db")
        self.environment = patch.dict(os.environ, {"MODEL_BACKEND": "local"})
        self.environment.start()
        for faq in FAQS:
            self.call(action="knowledge_upsert", document=faq)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()
        self.environment.stop()

    def call(self, **payload):
        response, _ = self.store.run({"tenant": "shop-a", "conversation_id": "thread-1", **payload}, uuid.uuid4().hex, process)
        return response["result"]

    def test_demo_answers_with_evidence(self):
        result = self.call(**{key: value for key, value in DEMO.items() if key not in {"tenant", "conversation_id"}})
        self.assertEqual(result["status"], "open")
        self.assertEqual(result["sources"][0]["document_id"], "returns")
        self.assertIn("treinta", result["answer"])

    def test_unknown_query_escalates(self):
        result = self.call(message="telescopio volcán astronomía")
        self.assertEqual(result["status"], "escalated")
        self.assertEqual(result["sources"], [])

    def test_explicit_handoff_overrides_available_answer(self):
        result = self.call(message="devolución producto plazo", ask_human=True)
        self.assertEqual(result["status"], "escalated")
        self.assertEqual(result["sources"], [])

    def test_explicit_handoff_does_not_depend_on_model_availability(self):
        with patch.dict(os.environ, {"MODEL_BACKEND": "ollama"}), patch("app.providers.structured", side_effect=ValueError("provider unavailable")) as provider:
            result = self.call(message="devolución producto plazo", ask_human=True)
        provider.assert_not_called()
        self.assertEqual(result["status"], "escalated")
        self.assertEqual(result["method"], "explicit-handoff")

    def test_escalated_conversation_stays_with_human(self):
        self.call(message="telescopio volcán")
        result = self.call(message="devolución producto")
        self.assertEqual(result["resolution"], "pending-human")

    def test_operator_resolves_escalated_conversation(self):
        self.call(message="telescopio volcán")
        result = self.call(action="resolve", operator="support-agent", resolution="Se contactó al cliente y se acordó seguimiento.")
        self.assertEqual(result["status"], "resolved")
        self.assertGreaterEqual(result["resolution_seconds"], 0)

    def test_open_conversation_cannot_be_resolved(self):
        self.call(message="devolución producto plazo")
        with self.assertRaisesRegex(ValueError, "only escalated"):
            self.call(action="resolve", operator="support-agent", resolution="Done")

    def test_closed_conversation_requires_new_id(self):
        self.call(message="telescopio volcán")
        self.call(action="resolve", operator="support-agent", resolution="Done")
        with self.assertRaisesRegex(ValueError, "closed"):
            self.call(message="devolución producto")

    def test_conversation_is_tenant_scoped(self):
        self.call(message="devolución producto")
        with self.assertRaisesRegex(ValueError, "not found"):
            self.call(tenant="shop-b", action="conversation")

    def test_knowledge_is_tenant_scoped(self):
        result = self.call(tenant="shop-b", message="devolución producto plazo")
        self.assertEqual(result["status"], "escalated")

    def test_persisted_contact_information_is_redacted(self):
        self.call(message="Mi correo persona@example.com y teléfono +593 994 203 888; devolución producto plazo")
        result = self.call(action="conversation")
        content = result["messages"][0]["content"]
        self.assertNotIn("persona@example.com", content)
        self.assertNotIn("994", content)
        self.assertIn("[correo]", content)
        self.assertIn("[teléfono]", content)

    def test_channel_cannot_change_within_conversation(self):
        self.call(message="devolución producto", channel="email")
        with self.assertRaisesRegex(ValueError, "channel cannot change"):
            self.call(message="devolución producto", channel="web")

    def test_empty_message_and_nonboolean_handoff_rejected(self):
        with self.assertRaises(ValueError):
            self.call(message="")
        with self.assertRaises(ValueError):
            self.call(message="devolución", ask_human="false")

    def test_knowledge_update_is_visible_with_version(self):
        self.call(action="knowledge_upsert", document=dict(FAQS[0], text="La devolución del producto requiere revisión en diez días.", expected_version=1))
        result = self.call(message="devolución producto")
        self.assertEqual(result["sources"][0]["version"], 2)
        self.assertIn("diez", result["answer"])

    def test_deleted_faq_no_longer_answers(self):
        self.call(action="knowledge_delete", document_id="returns")
        self.assertEqual(self.call(message="devolución producto")["status"], "escalated")

    def test_recreated_faq_keeps_monotonic_version_and_rejects_stale_write(self):
        before = self.call(message="devolución producto")["sources"][0]
        self.call(action="knowledge_delete", document_id="returns")
        recreated = self.call(action="knowledge_upsert", document=dict(FAQS[0], text="La devolución del producto requiere revisión en diez días."))
        self.assertEqual(recreated["version"], 3)
        after = self.call(message="devolución producto")["sources"][0]
        self.assertEqual(after["chunk_id"], before["chunk_id"])
        self.assertEqual(after["version"], 3)
        with self.assertRaisesRegex(ValueError, "version conflict"):
            self.call(action="knowledge_upsert", document=dict(FAQS[0], expected_version=1))
        self.assertIn("diez", self.call(message="devolución producto")["answer"])

    def test_delete_invalidates_predelete_expected_version(self):
        self.call(action="knowledge_delete", document_id="returns")
        for expected in (0, 1):
            with self.assertRaisesRegex(ValueError, "version conflict"):
                self.call(action="knowledge_upsert", document=dict(FAQS[0], expected_version=expected))

    def test_repeated_missing_delete_does_not_advance_revision(self):
        self.assertTrue(self.call(action="knowledge_delete", document_id="returns")["deleted"])
        self.assertFalse(self.call(action="knowledge_delete", document_id="returns")["deleted"])
        self.assertEqual(self.call(action="knowledge_upsert", document=FAQS[0])["version"], 3)

    def test_revision_ledger_is_tenant_scoped(self):
        self.call(action="knowledge_delete", document_id="returns")
        result = self.call(tenant="shop-b", action="knowledge_upsert", document=dict(FAQS[0], expected_version=0))
        self.assertEqual(result["version"], 1)
        self.assertEqual(self.call(action="knowledge_upsert", document=FAQS[0])["version"], 3)

    def test_delete_rollback_restores_index_and_revision(self):
        def fail_after_delete(payload, store):
            process({"tenant":"shop-a", "action":"knowledge_delete", "document_id":"returns"}, store)
            raise ValueError("later operation failed")
        with self.assertRaisesRegex(ValueError, "later operation"):
            self.store.run({}, uuid.uuid4().hex, fail_after_delete)
        self.assertEqual(self.call(message="devolución producto")["sources"][0]["version"], 1)
        self.call(action="knowledge_delete", document_id="returns")
        self.assertEqual(self.call(action="knowledge_upsert", document=FAQS[0])["version"], 3)

    def test_legacy_active_versions_backfill_revision_ledger(self):
        self.call(action="knowledge_upsert", document=dict(FAQS[0], text="La devolución del producto se solicita en diez días.", expected_version=1))
        self.store.connection.execute("DROP TABLE document_revisions")
        self.call(action="knowledge_delete", document_id="returns")
        self.assertEqual(self.call(action="knowledge_upsert", document=FAQS[0])["version"], 4)

    def test_retry_does_not_duplicate_conversation_turn(self):
        payload = {"tenant": "shop-a", "conversation_id": "retry-1", "message": "devolución producto plazo"}
        first, replay = self.store.run(payload, "incoming-message-1", process)
        second, replay_again = self.store.run(payload, "incoming-message-1", process)
        self.assertFalse(replay)
        self.assertTrue(replay_again)
        self.assertEqual(first, second)
        self.assertEqual(len(self.call(action="conversation", conversation_id="retry-1")["messages"]), 2)

    def test_domain_metrics_distinguish_pending_and_resolved(self):
        self.call(message="devolución producto")
        self.call(conversation_id="thread-2", message="telescopio volcán")
        before = self.call(action="metrics")
        self.assertEqual((before["open_conversations"], before["pending_human"], before["resolved_by_human"]), (1, 1, 0))
        self.assertIsNone(before["human_resolution_mean_seconds"])
        self.call(action="resolve", conversation_id="thread-2", operator="operator-1", resolution="Seguimiento acordado")
        after = self.call(action="metrics")
        self.assertEqual((after["pending_human"], after["resolved_by_human"]), (0, 1))
        self.assertGreaterEqual(after["human_resolution_mean_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
