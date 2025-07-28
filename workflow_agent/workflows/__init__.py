"""
Workflows package for the workflow agent.

This package contains:
- WorkflowOrchestrator: Manages workflow execution
- Predefined workflow templates
- Workflow state management
"""

from workflow_agent.workflows.orchestrator import WorkflowOrchestrator
from workflow_agent.workflows.templates import (
    EmailTriageWorkflow,
    ReportGenerationWorkflow,
    DataPipelineWorkflow,
)

__all__ = [
    "WorkflowOrchestrator",
    "EmailTriageWorkflow",
    "ReportGenerationWorkflow",
    "DataPipelineWorkflow",
]
