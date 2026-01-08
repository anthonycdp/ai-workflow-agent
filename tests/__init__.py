"""
Tests for AI Workflow Agent.
"""


def test_imports():
    """Test that all main modules can be imported."""
    from workflow_agent import (
        WorkflowAgent,
        EmailTool,
        ReportGeneratorTool,
        DataProcessingTool,
        NotificationTool,
        WorkflowOrchestrator,
        HumanApprovalMiddleware,
        RetryMiddleware,
        FallbackMiddleware,
    )

    assert WorkflowAgent is not None
    assert EmailTool is not None
    assert ReportGeneratorTool is not None
    assert DataProcessingTool is not None
    assert NotificationTool is not None
    assert WorkflowOrchestrator is not None
    assert HumanApprovalMiddleware is not None
    assert RetryMiddleware is not None
    assert FallbackMiddleware is not None
