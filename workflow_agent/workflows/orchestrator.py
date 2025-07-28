"""
Workflow orchestrator for managing and executing workflows.

The orchestrator coordinates between the agent, tools, and middleware
to execute complex multi-step workflows.
"""

import asyncio
import inspect
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from workflow_agent.agent import WorkflowAgent
from workflow_agent.config import AgentConfig
from workflow_agent.models import (
    WorkflowResult,
    WorkflowStatus,
    ApprovalDecision,
)


class WorkflowType(str, Enum):
    """Types of workflows available."""

    EMAIL_TRIAGE = "email_triage"
    REPORT_GENERATION = "report_generation"
    DATA_PIPELINE = "data_pipeline"
    CUSTOM = "custom"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    name: str
    action: str
    tool: str
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    on_failure: str = "abort"  # abort, skip, retry
    retry_count: int = 0


@dataclass
class Workflow:
    """Definition of a complete workflow."""

    id: str
    name: str
    description: str
    steps: list[WorkflowStep] = field(default_factory=list)
    workflow_type: WorkflowType = WorkflowType.CUSTOM
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowOrchestrator:
    """
    Orchestrates workflow execution with the AI agent.

    This class manages:
    - Workflow registration and storage
    - Sequential and parallel step execution
    - State management and persistence
    - Human-in-the-loop coordination
    - Error handling and recovery

    The orchestrator acts as the central coordinator between
    the agent, tools, and middleware components.

    Example:
        ```python
        orchestrator = WorkflowOrchestrator(agent)

        # Register a workflow
        orchestrator.register_workflow(email_triage_workflow)

        # Execute the workflow
        result = await orchestrator.execute("email_triage", context)
        ```
    """

    def __init__(
        self,
        agent: Optional[WorkflowAgent] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        Initialize the workflow orchestrator.

        Args:
            agent: WorkflowAgent instance (created if not provided)
            config: Agent configuration
        """
        self.agent = agent or WorkflowAgent(config=config)
        self.config = config or AgentConfig()

        # Workflow storage
        self._workflows: dict[str, Workflow] = {}
        self._active_executions: dict[str, WorkflowResult] = {}

        # Callbacks
        self._on_step_complete: Optional[Callable] = None
        self._on_workflow_complete: Optional[Callable] = None
        self._on_approval_required: Optional[Callable] = None

    async def _invoke_callback(self, callback: Optional[Callable], *args: Any) -> None:
        """Invoke sync or async callbacks transparently."""
        if not callback:
            return

        callback_result = callback(*args)
        if inspect.isawaitable(callback_result):
            await callback_result

    async def _sync_pending_approvals(self, result: WorkflowResult) -> bool:
        """Sync orchestrator state with the agent approval queue."""
        pending_approvals = self.agent.get_pending_approvals()
        if not pending_approvals:
            return False

        result.status = WorkflowStatus.WAITING_APPROVAL
        result.approvals_requested += len(pending_approvals)

        for approval in pending_approvals:
            await self._invoke_callback(self._on_approval_required, approval)

        if not self.config.auto_approve_safe_actions:
            return True

        for approval in pending_approvals:
            await self.agent.approve_action(approval.request_id, ApprovalDecision.APPROVE)
            result.approvals_granted += 1

        result.status = WorkflowStatus.RUNNING
        return False

    def _record_step_result(
        self,
        result: WorkflowResult,
        step_index: int,
        step_result: WorkflowResult,
    ) -> None:
        """Store a normalized step result payload."""
        result.output[f"step_{step_index}"] = {
            "status": step_result.status.value,
            "output": step_result.output,
            "error": step_result.errors[0] if step_result.errors else None,
        }

    async def _execute_step_with_retry(
        self,
        step: WorkflowStep,
        parameters: dict[str, Any],
        context: Optional[dict[str, Any]],
    ) -> WorkflowResult:
        """Execute a step and retry when configured."""
        step_result = await self._execute_step(step, parameters, context)
        retry_attempts = 0

        while (
            step_result.status == WorkflowStatus.FAILED
            and step.on_failure == "retry"
            and retry_attempts < 3
        ):
            retry_attempts += 1
            step_result = await self._execute_step(step, parameters, context)

        return step_result

    def register_workflow(self, workflow: Workflow) -> None:
        """
        Register a workflow with the orchestrator.

        Args:
            workflow: The workflow to register
        """
        self._workflows[workflow.id] = workflow

    def create_workflow(
        self,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        workflow_type: WorkflowType = WorkflowType.CUSTOM,
    ) -> Workflow:
        """
        Create and register a new workflow.

        Args:
            name: Workflow name
            description: Workflow description
            steps: List of step definitions
            workflow_type: Type of workflow

        Returns:
            The created Workflow
        """
        workflow_steps = [
            WorkflowStep(
                name=step.get("name", f"Step {i}"),
                action=step["action"],
                tool=step["tool"],
                parameters=step.get("parameters", {}),
                requires_approval=step.get("requires_approval", False),
                on_failure=step.get("on_failure", "abort"),
            )
            for i, step in enumerate(steps)
        ]

        workflow = Workflow(
            id=name.lower().replace(" ", "_"),
            name=name,
            description=description,
            steps=workflow_steps,
            workflow_type=workflow_type,
        )

        self.register_workflow(workflow)
        return workflow

    async def execute(
        self,
        workflow_id: str,
        context: Optional[dict[str, Any]] = None,
        variables: Optional[dict[str, Any]] = None,
    ) -> WorkflowResult:
        """
        Execute a registered workflow.

        Args:
            workflow_id: ID of the workflow to execute
            context: Execution context
            variables: Variables to substitute in parameters

        Returns:
            WorkflowResult with execution details
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        execution_id = str(uuid.uuid4())
        result = WorkflowResult(
            workflow_id=execution_id,
            status=WorkflowStatus.RUNNING,
            steps_total=len(workflow.steps),
        )

        self._active_executions[execution_id] = result

        try:
            for i, step in enumerate(workflow.steps):
                result.status = WorkflowStatus.RUNNING

                if await self._sync_pending_approvals(result):
                    break

                params = self._substitute_variables(step.parameters, variables or {})
                step_result = await self._execute_step_with_retry(step, params, context)
                self._record_step_result(result, i, step_result)

                if step_result.status == WorkflowStatus.WAITING_APPROVAL:
                    await self._sync_pending_approvals(result)
                    break

                if step_result.status != WorkflowStatus.COMPLETED:
                    error_message = step_result.errors[0] if step_result.errors else "Unknown error"
                    result.errors.append(f"Step {step.name} failed: {error_message}")

                    if step.on_failure == "skip":
                        continue

                    result.status = WorkflowStatus.FAILED
                    break

                result.steps_completed += 1
                await self._invoke_callback(self._on_step_complete, workflow, step, step_result)

            if result.status == WorkflowStatus.RUNNING:
                result.status = WorkflowStatus.COMPLETED

        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.errors.append(str(e))
        finally:
            result.completed_at = datetime.now()
            await self._invoke_callback(self._on_workflow_complete, workflow, result)
            self._active_executions.pop(execution_id, None)

        return result

    async def _execute_step(
        self,
        step: WorkflowStep,
        parameters: dict[str, Any],
        context: Optional[dict[str, Any]],
    ) -> WorkflowResult:
        """Execute a single workflow step."""
        task = f"{step.action} using {step.tool}"
        if parameters:
            task += f" with parameters: {parameters}"

        return await self.agent.process(task, context)

    def _substitute_variables(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Substitute variables in parameter values."""
        result = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                result[key] = variables.get(var_name, value)
            elif isinstance(value, dict):
                result[key] = self._substitute_variables(value, variables)
            else:
                result[key] = value
        return result

    async def execute_parallel(
        self,
        workflow_ids: list[str],
        contexts: Optional[list[dict[str, Any]]] = None,
    ) -> list[WorkflowResult]:
        """
        Execute multiple workflows in parallel.

        Args:
            workflow_ids: List of workflow IDs to execute
            contexts: Optional contexts for each workflow

        Returns:
            List of WorkflowResults
        """
        tasks = []
        for i, workflow_id in enumerate(workflow_ids):
            context = contexts[i] if contexts and i < len(contexts) else None
            tasks.append(self.execute(workflow_id, context))

        return await asyncio.gather(*tasks)

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a registered workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[Workflow]:
        """List all registered workflows."""
        return list(self._workflows.values())

    def get_active_executions(self) -> dict[str, WorkflowResult]:
        """Get all currently active executions."""
        return self._active_executions.copy()

    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel an active execution.

        Args:
            execution_id: ID of the execution to cancel

        Returns:
            True if cancelled successfully
        """
        result = self._active_executions.get(execution_id)
        if result and result.status == WorkflowStatus.RUNNING:
            result.status = WorkflowStatus.CANCELLED
            result.completed_at = datetime.now()
            return True
        return False

    def on_step_complete(self, callback: Callable) -> None:
        """Set callback for step completion."""
        self._on_step_complete = callback

    def on_workflow_complete(self, callback: Callable) -> None:
        """Set callback for workflow completion."""
        self._on_workflow_complete = callback

    def on_approval_required(self, callback: Callable) -> None:
        """Set callback for approval requests."""
        self._on_approval_required = callback

    def get_execution_status(self, execution_id: str) -> Optional[WorkflowResult]:
        """Get the status of an execution."""
        return self._active_executions.get(execution_id)

    def get_execution_history(self) -> list[WorkflowResult]:
        """Get history of all executions."""
        return self.agent.get_workflow_history()
