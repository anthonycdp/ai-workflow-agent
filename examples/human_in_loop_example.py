"""
Human-in-the-loop example for the AI Workflow Agent.

This example demonstrates:
- Human approval workflows
- Sensitive action detection
- Approval request handling
- Custom approval handlers
"""

import asyncio
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow_agent.middleware.human_approval import (
    HumanApprovalMiddleware,
    ApprovalHandler,
)
from workflow_agent.middleware.retry import RetryMiddleware
from workflow_agent.middleware.fallback import FallbackMiddleware, FallbackStrategy
from workflow_agent.models import ApprovalDecision, ApprovalRequest


class LoggingApprovalHandler(ApprovalHandler):
    """Custom approval handler that logs requests and auto-decides based on rules."""

    def __init__(self):
        self.requests_log = []

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Handle approval request with custom logic."""
        # Log the request
        self.requests_log.append(
            {
                "request_id": request.request_id,
                "tool_name": request.tool_name,
                "risk_level": request.risk_level,
                "timestamp": datetime.now().isoformat(),
            }
        )

        print(f"\n   [APPROVAL REQUEST] {request.tool_name}")
        print(f"   Risk Level: {request.risk_level}")
        print(f"   Description: {request.action_description}")

        # Custom auto-approval rules
        if request.risk_level == "low":
            print("   -> Auto-approved (low risk)")
            return ApprovalDecision.APPROVE

        if request.risk_level == "critical":
            print("   -> Auto-rejected (critical risk - needs manual review)")
            return ApprovalDecision.REJECT

        # For medium/high risk, simulate user approval
        print("   -> Simulated user approval")
        return ApprovalDecision.APPROVE


async def main():
    """Run human-in-the-loop example."""
    print("=" * 70)
    print("AI Workflow Agent - Human-in-the-Loop Example")
    print("=" * 70)

    # 1. Create custom approval handler
    print("\n1. Setting up custom approval handler...")
    handler = LoggingApprovalHandler()

    middleware = HumanApprovalMiddleware(
        auto_approve_safe=True,
        sensitive_actions=[
            "send_email",
            "delete_data",
            "external_api_call",
            "modify_settings",
        ],
        approval_handler=handler,
    )

    print("   Sensitive actions configured:")
    for action in middleware.sensitive_actions:
        print(f"   - {action}")

    # 2. Test risk assessment
    print("\n2. Testing risk level assessment...")
    test_actions = [
        ("read_data", {}, "low"),
        ("send_email", {"to": "user@example.com"}, "high"),
        ("delete_all_records", {}, "critical"),
        ("update_config", {"key": "value"}, "medium"),
    ]

    for action, args, expected in test_actions:
        risk = middleware.assess_risk_level(action, args)
        status = "✓" if risk == expected else "✗"
        print(f"   {status} {action}: {risk} (expected: {expected})")

    # 3. Test approval requirement detection
    print("\n3. Testing approval requirement detection...")
    test_cases = [
        ("list_items", {}, False),
        ("send_email", {"to": "test@example.com"}, True),
        ("delete_data", {"id": 123}, True),
        ("search", {"query": "test"}, False),
    ]

    for action, args, expected_approval in test_cases:
        requires = middleware.requires_approval(action, args)
        status = "✓" if requires == expected_approval else "✗"
        print(f"   {status} {action}: requires_approval={requires}")

    # 4. Create and process approval requests
    print("\n4. Creating approval requests...")

    requests = [
        {
            "action": "send_email",
            "args": {
                "to": "team@company.com",
                "subject": "Weekly Update",
                "body": "Here's the weekly update...",
            },
            "expected_risk": "high",
        },
        {
            "action": "read_config",
            "args": {"key": "theme"},
            "expected_risk": "low",
        },
        {
            "action": "delete_data",
            "args": {"table": "temp_cache"},
            "expected_risk": "critical",
        },
    ]

    for req_data in requests:
        request = await middleware.create_approval_request(
            req_data["action"],
            req_data["args"],
        )

        print(f"\n   Request ID: {request.request_id[:8]}...")
        print(f"   Action: {request.tool_name}")
        print(f"   Risk Level: {request.risk_level}")

        # Process the approval
        decision = await middleware.request_approval(request.request_id)
        print(f"   Decision: {decision.value}")

    # 5. Show approval history
    print("\n5. Approval request history:")
    for log_entry in handler.requests_log:
        print(f"   - {log_entry['tool_name']} ({log_entry['risk_level']})")

    # 6. Demonstrate retry middleware
    print("\n6. Retry middleware demonstration...")

    retry_middleware = RetryMiddleware(
        max_retries=3,
        delay=0.1,
        backoff=2.0,
        jitter=False,
    )

    call_count = 0

    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Simulated connection failure")
        return "Success!"

    try:
        result = await retry_middleware.execute(flaky_operation)
        print(f"   Result after {call_count} attempts: {result}")
        print(f"   Total retries: {retry_middleware._total_retries}")
    except Exception as e:
        print(f"   Failed after retries: {e}")

    # 7. Demonstrate fallback middleware
    print("\n7. Fallback middleware demonstration...")

    fallback_middleware = FallbackMiddleware(
        default_strategy=FallbackStrategy.SKIP,
        fallbacks={
            "important_action": {"strategy": "default_value", "default_value": "fallback_result"},
        },
    )

    # Test fallback for unknown action
    result = await fallback_middleware.handle_failure(
        ValueError("Test error"),
        "unknown_action",
    )
    fallback_data = json.loads(result)
    print(f"   Unknown action fallback: {fallback_data.get('skipped', False)}")

    # Test fallback for registered action
    result = await fallback_middleware.handle_failure(
        ValueError("Test error"),
        "important_action",
    )
    print(f"   Registered action fallback: {result}")

    # Show fallback statistics
    stats = fallback_middleware.get_statistics()
    print(f"   Fallback statistics: {stats}")

    # 8. Summary
    print("\n" + "=" * 70)
    print("Human-in-the-Loop Example Complete!")
    print("=" * 70)
    print("\nKey Concepts Demonstrated:")
    print("1. Custom approval handlers enable flexible approval workflows")
    print("2. Risk levels help categorize actions by potential impact")
    print("3. Sensitive actions are automatically flagged for review")
    print("4. Retry middleware handles transient failures")
    print("5. Fallback middleware provides graceful degradation")


if __name__ == "__main__":
    asyncio.run(main())
