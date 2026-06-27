"""B 成员：Chat Agent 工具与知识库回归测试。"""

import inspect
import json
import unittest
from unittest.mock import AsyncMock, patch

import chat_agent
from kb_bridge import (
    get_credit_tolerance,
    get_industry_rules,
    search_banks,
    search_cases,
    search_policies,
)


class TestKnowledgeBridge(unittest.TestCase):
    def test_chinese_policy_question_returns_guangdong_policy(self):
        rows = search_policies("广东制造业小微企业有什么政策支持？")
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(any(row.get("province") == "广东省" for row in rows))

    def test_chinese_industry_aliases_work_for_banks_cases_and_rules(self):
        self.assertGreaterEqual(len(search_banks("餐饮", requested_amount_wan=20)), 1)
        self.assertGreaterEqual(len(search_cases("住宿餐饮")), 1)
        self.assertEqual(get_industry_rules("餐饮").get("行业代码"), "hospitality_food")

    def test_tax_level_can_be_used_for_bank_ranking(self):
        rows = search_banks(requested_amount_wan=20, tax_level="A")
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(rows[0]["tax_level_match"])

    def test_credit_tolerance_uses_real_csv_column(self):
        rows = get_credit_tolerance("国有大型商业银行")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["银行层级"], "国有大行")


class TestAgentTools(unittest.IsolatedAsyncioTestCase):
    def test_evaluation_schema_uses_backend_field_names(self):
        fields = chat_agent.EVALUATION_TOOL_SCHEMA["function"]["parameters"]["properties"]
        for name in (
            "requested_amount",
            "loan_term",
            "operating_years",
            "monthly_revenue",
            "overdue_count_2yr",
        ):
            self.assertIn(name, fields)
        for old_name in ("amount", "term_years", "business_years", "annual_revenue", "credit_overdues"):
            self.assertNotIn(old_name, fields)

    async def test_evaluate_loan_returns_explainable_backend_fields(self):
        result = await chat_agent._evaluate_loan_tool(
            requested_amount=200000,
            loan_term=12,
            industry="餐饮",
            operating_years=2,
            monthly_revenue=60000,
            monthly_fixed_cost=30000,
            tax_level="A",
        )
        self.assertTrue(result["success"])
        self.assertIn(result["risk_level"], {"low", "medium", "high"})
        self.assertIn("enterprise_health_score", result)
        self.assertIn("improvement_tips", result)
        self.assertGreaterEqual(len(result["bank_matches"]), 1)
        self.assertIn("estimated_interest_rate", result["bank_matches"][0])
        self.assertIn("recommendation_reasons", result["bank_matches"][0])
        self.assertGreaterEqual(len(result["recommended_materials"]), 1)

    async def test_async_and_sync_tools_are_both_awaited(self):
        stress = await chat_agent._execute_tool(
            "run_stress_test",
            {"monthly_revenue": 60000, "monthly_fixed_cost": 30000, "monthly_repayment": 10000},
        )
        policies = await chat_agent._execute_tool(
            "search_policies",
            {"query": "广东制造业小微企业有什么政策支持？"},
        )
        self.assertIsInstance(stress, dict)
        self.assertTrue(stress["success"])
        self.assertFalse(inspect.isawaitable(stress))
        self.assertIsInstance(policies, list)

    async def test_enterprise_search_tool_returns_structured_result(self):
        result = await chat_agent._execute_tool("search_enterprise", {"name": "餐饮"})
        self.assertTrue(result["found"])
        self.assertIn("score", result)
        self.assertIn("risk_level", result)

    async def test_no_key_fails_clearly_instead_of_generating_fallback_advice(self):
        with patch.object(chat_agent, "DEEPSEEK_API_KEY", ""):
            with self.assertRaises(chat_agent.AgentConfigurationError):
                await chat_agent.run_agent("我开餐饮店2年，月流水6万，想贷20万，可以吗？")

    async def test_agent_loop_serializes_real_tool_result(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        class FakeAsyncClient:
            responses = [
                {
                    "choices": [{
                        "finish_reason": "tool_calls",
                        "message": {
                            "content": "",
                            "tool_calls": [{
                                "id": "call-evaluate",
                                "function": {
                                    "name": "evaluate_loan",
                                    "arguments": json.dumps({
                                        "requested_amount": 200000,
                                        "loan_term": 12,
                                        "industry": "餐饮",
                                        "operating_years": 2,
                                        "monthly_revenue": 60000,
                                    }, ensure_ascii=False),
                                },
                            }],
                        },
                    }],
                },
                {
                    "choices": [{
                        "finish_reason": "stop",
                        "message": {"content": "已基于评估工具生成建议。"},
                    }],
                },
            ]
            requests = []

            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                self.__class__.requests.append(kwargs["json"])
                return FakeResponse(self.__class__.responses.pop(0))

        chat_agent._active_sessions.clear()
        with (
            patch.object(chat_agent, "DEEPSEEK_API_KEY", "sk-test"),
            patch.object(chat_agent.httpx, "AsyncClient", FakeAsyncClient),
        ):
            reply = await chat_agent.run_agent("我开餐饮店2年，月流水6万，想贷20万，可以吗？", "test-session")

        self.assertEqual(reply, "已基于评估工具生成建议。")
        tool_messages = [
            message
            for message in FakeAsyncClient.requests[1]["messages"]
            if message.get("role") == "tool"
        ]
        self.assertEqual(len(tool_messages), 1)
        tool_result = json.loads(tool_messages[0]["content"])
        self.assertTrue(tool_result["success"])
        self.assertIn("enterprise_health_score", tool_result)
        self.assertIn("improvement_tips", tool_result)


class TestAgentApiIntegration(unittest.TestCase):
    def test_stream_endpoint_reuses_function_call_agent(self):
        from fastapi.testclient import TestClient
        import main

        fake_run_agent = AsyncMock(return_value="已调用评估和知识库工具生成建议。")
        with (
            patch.object(main, "is_llm_available", return_value=True),
            patch.object(main, "run_agent", fake_run_agent),
        ):
            response = TestClient(main.app).post(
                "/api/chat/stream",
                json={"query": "广东制造业有什么政策？", "session_id": "stream-test"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("已调用评估和知识库工具生成建议。", response.text)
        fake_run_agent.assert_awaited_once_with("广东制造业有什么政策？", "stream-test")


if __name__ == "__main__":
    unittest.main()
