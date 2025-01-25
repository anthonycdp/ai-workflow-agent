"""
AI Workflow Agent - A robust agent framework for workflow automation.

This package provides an AI agent that automates workflows with:
- Human-in-the-loop supervision
- Fallback mechanisms
- Tool use capabilities
- Comprehensive error handling
"""

from workflow_agent.agent import WorkflowAgent
from workflow_agent.tools import (
    EmailTool,
    ReportGeneratorTool,
    DataProcessingTool,
    NotificationTool,
)
from workflow_agent.workflows import WorkflowOrchestrator
from workflow_agent.middleware import (
    HumanApprovalMiddleware,
    RetryMiddleware,
    FallbackMiddleware,
)

__version__ = "1.0.0"
__all__ = [
    "WorkflowAgent",
    "EmailTool",
    "ReportGeneratorTool",
    "DataProcessingTool",
    "NotificationTool",
    "WorkflowOrchestrator",
    "HumanApprovalMiddleware",
    "RetryMiddleware",
    "FallbackMiddleware",
]
