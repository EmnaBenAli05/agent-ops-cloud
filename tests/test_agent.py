import unittest

from agent_ops.agent import execute_tool, run_agent
from agent_ops.audit import AuditLog
from agent_ops.llm import ScriptedBackend
from agent_ops.tools import TOOLS, OpsEnvironment
from evals.scenarios import evaluate


def approve(*_):
    return True


class GuardrailTests(unittest.TestCase):
    def setUp(self):
        self.env, self.audit = OpsEnvironment(), AuditLog()

    def run_tool(self, name, args, approver=approve):
        return execute_tool(name, args, self.env, approver, self.audit, "TEST")

    def test_unknown_tool_is_rejected(self):
        content, is_error = self.run_tool("delete_database", {})
        self.assertTrue(is_error)
        self.assertEqual(self.audit.entries[-1]["decision"], "rejected")

    def test_invalid_service_never_reaches_operator(self):
        asked = []
        _, is_error = self.run_tool("restart_service", {"service": "*", "reason": "test de validation"},
                                    approver=lambda *a: asked.append(a) or True)
        self.assertTrue(is_error)
        self.assertEqual(asked, [])
        self.assertEqual(self.env.restarted, [])

    def test_operator_refusal_blocks_action(self):
        _, is_error = self.run_tool("restart_service",
                                    {"service": "api-paiement", "reason": "pool SQL saturé"},
                                    approver=lambda *_: False)
        self.assertTrue(is_error)
        self.assertEqual(self.env.restarted, [])
        self.assertEqual(self.audit.entries[-1]["decision"], "denied")

    def test_read_only_tools_need_no_approval(self):
        _, is_error = self.run_tool("get_metrics", {"service": "api-paiement"},
                                    approver=lambda *_: self.fail("approbation demandée"))
        self.assertFalse(is_error)

    def test_log_limit_is_validated(self):
        _, is_error = self.run_tool("search_logs", {"service": "api-paiement", "level": "INFO", "limit": 500})
        self.assertTrue(is_error)

    def test_only_restart_is_sensitive(self):
        self.assertEqual([t.name for t in TOOLS.values() if t.sensitive], ["restart_service"])

    def test_schemas_are_strict(self):
        for tool in TOOLS.values():
            api = tool.to_api()
            self.assertTrue(api["strict"])
            self.assertFalse(api["input_schema"]["additionalProperties"])


class LoopTests(unittest.TestCase):
    def test_max_rounds_stops_the_loop(self):
        result = run_agent("ALT-001", ScriptedBackend(), approver=approve, max_rounds=2)
        self.assertEqual(result.stop, "max_rounds")

    def test_all_scenarios_pass_offline(self):
        failed = [(s, label) for s, label, ok in evaluate(ScriptedBackend) if not ok]
        self.assertEqual(failed, [])


if __name__ == "__main__":
    unittest.main()
