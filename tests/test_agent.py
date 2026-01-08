"""
Tests for WorkflowAgent behavior.
"""

import os
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from workflow_agent.agent import WorkflowAgent
from workflow_agent.config import AgentConfig, LLMProvider
from workflow_agent.models import ApprovalDecision, WorkflowStatus


class DummyLLM:
    """Minimal LLM stub for deterministic agent tests."""

    def __init__(self, responses: list[AIMessage]):
        self._responses = responses

    def bind_tools(self, tools: list[Any]) -> "DummyLLM":
        return self

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        return self._responses.pop(0)


def build_agent(auto_approve: bool, calls: list[dict[str, Any]]) -> WorkflowAgent:
    """Create an agent with a stub tool and deterministic LLM."""
    os.environ.setdefault("OPENAI_API_KEY", "test-key")

    async def send_email(action: str, to: str, subject: str, body: str) -> str:
        calls.append(
            {
                "action": action,
                "to": to,
                "subject": subject,
                "body": body,
            }
        )
        return "sent"

    tool = StructuredTool.from_function(
        coroutine=send_email,
        name="email_tool",
        description="Send an email message.",
    )
    config = AgentConfig(
        llm_provider=LLMProvider.OPENAI,
        auto_approve_safe_actions=auto_approve,
        sensitive_actions=["send"],
    )
    agent = WorkflowAgent(config=config, tools=[tool])
    agent.llm = DummyLLM(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "email_tool",
                        "args": {
                            "action": "send",
                            "to": "test@example.com",
                            "subject": "Status",
                            "body": "Please review.",
                        },
                        "id": "call_1",
                    }
                ],
            )
        ]
    )
    return agent


@pytest.mark.asyncio
async def test_process_pauses_for_pending_approval():
    """Agent should stop the loop when a tool requires human approval."""
    calls: list[dict[str, Any]] = []
    agent = build_agent(auto_approve=False, calls=calls)

    result = await agent.process("Send a status email")

    pending = agent.get_pending_approvals()
    assert result.status == WorkflowStatus.WAITING_APPROVAL
    assert len(pending) == 1
    assert calls == []
    assert result.output["pending_approval"]["request_id"] == pending[0].request_id


@pytest.mark.asyncio
async def test_approve_action_executes_pending_tool():
    """Approving a queued action should execute the tool and clear the queue."""
    calls: list[dict[str, Any]] = []
    agent = build_agent(auto_approve=False, calls=calls)

    await agent.process("Send a status email")
    pending_request = agent.get_pending_approvals()[0]

    approval_result = await agent.approve_action(
        pending_request.request_id,
        ApprovalDecision.APPROVE,
    )

    assert approval_result.success is True
    assert len(calls) == 1
    assert agent.get_pending_approvals() == []


@pytest.mark.asyncio
async def test_reject_action_clears_pending_tool():
    """Rejecting a queued action should clear the queue without executing the tool."""
    calls: list[dict[str, Any]] = []
    agent = build_agent(auto_approve=False, calls=calls)

    await agent.process("Send a status email")
    pending_request = agent.get_pending_approvals()[0]

    rejection_result = await agent.approve_action(
        pending_request.request_id,
        ApprovalDecision.REJECT,
    )

    assert rejection_result.success is False
    assert "rejected" in (rejection_result.error or "").lower()
    assert calls == []
    assert agent.get_pending_approvals() == []
