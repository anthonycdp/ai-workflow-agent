"""
Tests for AI Workflow Agent middleware.
"""

import pytest
import asyncio

from workflow_agent.middleware.human_approval import (
    HumanApprovalMiddleware,
    ApprovalHandler,
)
from workflow_agent.middleware.retry import RetryMiddleware
from workflow_agent.middleware.fallback import (
    FallbackMiddleware,
    FallbackStrategy,
    FallbackChain,
)
from workflow_agent.models import ApprovalDecision, ApprovalRequest


class MockApprovalHandler(ApprovalHandler):
    """Mock approval handler for testing."""

    def __init__(self, decision: ApprovalDecision = ApprovalDecision.APPROVE):
        self.decision = decision
        self.requests = []

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        self.requests.append(request)
        return self.decision


class TestHumanApprovalMiddleware:
    """Tests for HumanApprovalMiddleware."""

    def test_requires_approval_sensitive_action(self):
        """Test that sensitive actions require approval."""
        middleware = HumanApprovalMiddleware(sensitive_actions=["send_email", "delete"])

        assert middleware.requires_approval("send_email", {}) is True
        assert middleware.requires_approval("delete", {}) is True
        assert middleware.requires_approval("read", {}) is False

    def test_requires_approval_auto_approve_disabled(self):
        """Test that all actions require approval when auto-approve is off."""
        middleware = HumanApprovalMiddleware(
            auto_approve_safe=False,
            sensitive_actions=["send_email"],
        )

        assert middleware.requires_approval("read", {}) is True
        assert middleware.requires_approval("send_email", {}) is True

    def test_assess_risk_level(self):
        """Test risk level assessment."""
        middleware = HumanApprovalMiddleware()

        assert middleware.assess_risk_level("delete_data", {}) == "critical"
        assert middleware.assess_risk_level("send_email", {}) == "high"
        assert middleware.assess_risk_level("update_config", {}) == "medium"
        assert middleware.assess_risk_level("read_data", {}) == "low"

    @pytest.mark.asyncio
    async def test_create_approval_request(self):
        """Test creating an approval request."""
        middleware = HumanApprovalMiddleware()

        request = await middleware.create_approval_request(
            "send_email",
            {"to": "test@example.com", "subject": "Test"},
            {"user": "admin"},
        )

        assert request.tool_name == "send_email"
        assert request.proposed_input["to"] == "test@example.com"
        assert request.risk_level in ["low", "medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_request_approval(self):
        """Test the approval request flow."""
        handler = MockApprovalHandler(ApprovalDecision.APPROVE)
        middleware = HumanApprovalMiddleware(approval_handler=handler)

        request = await middleware.create_approval_request("send_email", {})
        decision = await middleware.request_approval(request.request_id)

        assert decision == ApprovalDecision.APPROVE
        assert len(handler.requests) == 1

    def test_add_remove_sensitive_action(self):
        """Test adding and removing sensitive actions."""
        middleware = HumanApprovalMiddleware(sensitive_actions=["send"])

        middleware.add_sensitive_action("delete")
        assert "delete" in middleware.sensitive_actions

        middleware.remove_sensitive_action("delete")
        assert "delete" not in middleware.sensitive_actions


class TestRetryMiddleware:
    """Tests for RetryMiddleware."""

    def test_calculate_delay(self):
        """Test delay calculation with exponential backoff."""
        middleware = RetryMiddleware(
            delay=1.0,
            backoff=2.0,
            max_delay=10.0,
            jitter=False,
        )

        assert middleware.calculate_delay(0) == 1.0
        assert middleware.calculate_delay(1) == 2.0
        assert middleware.calculate_delay(2) == 4.0
        assert middleware.calculate_delay(10) == 10.0  # Capped at max

    def test_should_retry(self):
        """Test retry condition checking."""
        middleware = RetryMiddleware()

        assert middleware.should_retry(ConnectionError()) is True
        assert middleware.should_retry(TimeoutError()) is True
        assert middleware.should_retry(ValueError()) is False

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution."""
        middleware = RetryMiddleware(max_retries=3)

        async def success_func():
            return "success"

        result = await middleware.execute(success_func)
        assert result == "success"
        assert middleware._total_retries == 0

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self):
        """Test retry followed by success."""
        middleware = RetryMiddleware(max_retries=3, delay=0.01)

        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Failed")
            return "success"

        result = await middleware.execute(flaky_func)
        assert result == "success"
        assert middleware._total_retries >= 1
        assert middleware._successful_retries >= 1

    @pytest.mark.asyncio
    async def test_execute_max_retries_exceeded(self):
        """Test failure after max retries."""
        middleware = RetryMiddleware(max_retries=2, delay=0.01)

        async def always_fail():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await middleware.execute(always_fail)

        assert middleware._failed_after_retries == 1

    def test_get_statistics(self):
        """Test statistics retrieval."""
        middleware = RetryMiddleware()
        stats = middleware.get_statistics()

        assert "total_retries" in stats
        assert "successful_retries" in stats
        assert "failed_after_retries" in stats


class TestFallbackMiddleware:
    """Tests for FallbackMiddleware."""

    def test_get_fallback_config(self):
        """Test fallback configuration retrieval."""
        middleware = FallbackMiddleware(fallbacks={"send_email": {"strategy": "skip"}})

        config = middleware.get_fallback_config("send_email")
        assert config["strategy"] == "skip"

        # Default fallback for unknown actions
        config = middleware.get_fallback_config("unknown_action")
        assert config["strategy"] == middleware.default_strategy

    @pytest.mark.asyncio
    async def test_handle_failure_default_value(self):
        """Test fallback with default value."""
        middleware = FallbackMiddleware(default_strategy=FallbackStrategy.DEFAULT_VALUE)

        result = await middleware.handle_failure(
            ValueError("Test error"),
            "test_action",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_failure_skip(self):
        """Test fallback with skip strategy."""
        middleware = FallbackMiddleware(default_strategy=FallbackStrategy.SKIP)

        result = await middleware.handle_failure(
            ValueError("Test error"),
            "test_action",
        )

        import json

        data = json.loads(result)
        assert data["skipped"] is True

    @pytest.mark.asyncio
    async def test_handle_failure_disabled(self):
        """Test that disabled fallback returns None."""
        middleware = FallbackMiddleware(enabled=False)

        result = await middleware.handle_failure(
            ValueError("Test error"),
            "test_action",
        )

        assert result is None

    def test_register_fallback(self):
        """Test registering a fallback."""
        middleware = FallbackMiddleware()

        middleware.register_fallback(
            "custom_action",
            FallbackStrategy.SIMPLIFIED,
            custom_param="value",
        )

        assert "custom_action" in middleware.fallbacks
        assert middleware.fallbacks["custom_action"]["strategy"] == "simplified"

    def test_fallback_history(self):
        """Test fallback event history."""
        middleware = FallbackMiddleware()
        assert middleware.get_fallback_history() == []

        # After handling a failure, history should have entries
        asyncio.run(middleware.handle_failure(ValueError(), "test"))

        history = middleware.get_fallback_history()
        assert len(history) == 1

    def test_get_statistics(self):
        """Test fallback statistics."""
        middleware = FallbackMiddleware()
        stats = middleware.get_statistics()

        assert "total_fallbacks" in stats


class TestFallbackChain:
    """Tests for FallbackChain."""

    @pytest.mark.asyncio
    async def test_chain_execution(self):
        """Test fallback chain tries strategies in order."""
        chain = FallbackChain(
            [
                FallbackStrategy.SKIP,
                FallbackStrategy.DEFAULT_VALUE,
            ]
        )

        result = await chain.execute(
            ValueError("Test"),
            "test_action",
        )

        # Should return a result from the first successful strategy
        assert result is not None
