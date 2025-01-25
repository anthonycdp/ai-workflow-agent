"""
Data models for the workflow agent.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalDecision(str, Enum):
    """Human approval decisions."""

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    DEFER = "defer"


class Priority(str, Enum):
    """Priority levels for tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Email(BaseModel):
    """Email data model."""

    id: str
    sender: str
    subject: str
    body: str
    received_at: datetime = Field(default_factory=datetime.now)
    priority: Priority = Priority.MEDIUM
    category: Optional[str] = None
    action_required: bool = False
    summary: Optional[str] = None


class ReportRequest(BaseModel):
    """Report generation request."""

    report_type: str
    title: str
    data_source: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    format: str = "markdown"
    include_charts: bool = False
    recipients: list[str] = Field(default_factory=list)


class Report(BaseModel):
    """Generated report."""

    id: str
    title: str
    content: str
    format: str
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataRecord(BaseModel):
    """Generic data record for processing."""

    id: str
    data: dict[str, Any]
    source: str
    processed: bool = False
    errors: list[str] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    """Result of a workflow execution."""

    workflow_id: str
    status: WorkflowStatus
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    steps_completed: int = 0
    steps_total: int = 0
    output: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    approvals_requested: int = 0
    approvals_granted: int = 0


class ToolResult(BaseModel):
    """Result from a tool execution."""

    success: bool
    output: Any
    error: Optional[str] = None
    requires_approval: bool = False
    approval_request: Optional[dict[str, Any]] = None


class AgentAction(BaseModel):
    """An action taken by the agent."""

    action_type: str
    tool_name: str
    tool_input: dict[str, Any]
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ApprovalRequest(BaseModel):
    """Request for human approval."""

    request_id: str
    tool_name: str
    action_description: str
    proposed_input: dict[str, Any]
    risk_level: str = "medium"
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    decision: Optional[ApprovalDecision] = None
    modified_input: Optional[dict[str, Any]] = None
    feedback: Optional[str] = None
