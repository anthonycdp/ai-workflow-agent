"""
Tests for AI Workflow Agent workflow orchestrator.
"""

import pytest

from workflow_agent.workflows.orchestrator import (
    WorkflowOrchestrator,
    Workflow,
    WorkflowStep,
    WorkflowType,
)
from workflow_agent.workflows.templates import (
    EmailTriageWorkflow,
    ReportGenerationWorkflow,
    DataPipelineWorkflow,
    get_template,
    list_templates,
)
from workflow_agent.config import AgentConfig
from workflow_agent.models import ApprovalRequest, ToolResult, WorkflowResult, WorkflowStatus


class StubAgent:
    """Simple agent stub for orchestrator tests."""

    def __init__(self, step_results):
        self.step_results = step_results
        self.pending_approvals: list[ApprovalRequest] = []

    async def process(self, task, context):
        return self.step_results.pop(0)

    def get_pending_approvals(self):
        return self.pending_approvals.copy()

    async def approve_action(self, request_id, decision, modified_input=None):
        self.pending_approvals = [
            request for request in self.pending_approvals if request.request_id != request_id
        ]
        return ToolResult(success=True, output={"request_id": request_id})

    def get_workflow_history(self):
        return []


class TestWorkflowOrchestrator:
    """Tests for WorkflowOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        return WorkflowOrchestrator()

    def test_register_workflow(self, orchestrator):
        """Test registering a workflow."""
        workflow = Workflow(
            id="test_workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=[
                WorkflowStep(
                    name="Step 1",
                    action="Do something",
                    tool="test_tool",
                )
            ],
        )

        orchestrator.register_workflow(workflow)

        assert orchestrator.get_workflow("test_workflow") == workflow

    def test_create_workflow(self, orchestrator):
        """Test creating a workflow from steps."""
        steps = [
            {
                "name": "First Step",
                "action": "Process data",
                "tool": "data_processor",
                "parameters": {"action": "analyze"},
            },
            {
                "name": "Second Step",
                "action": "Generate report",
                "tool": "report_generator",
                "parameters": {"format": "markdown"},
                "requires_approval": True,
            },
        ]

        workflow = orchestrator.create_workflow(
            name="Test Workflow",
            description="Created from steps",
            steps=steps,
        )

        assert workflow.id == "test_workflow"
        assert len(workflow.steps) == 2
        assert workflow.steps[1].requires_approval is True

    def test_list_workflows(self, orchestrator):
        """Test listing workflows."""
        workflow = Workflow(
            id="test",
            name="Test",
            description="Test",
            steps=[],
        )
        orchestrator.register_workflow(workflow)

        workflows = orchestrator.list_workflows()
        assert len(workflows) >= 1
        assert any(w.id == "test" for w in workflows)

    def test_substitute_variables(self, orchestrator):
        """Test variable substitution in parameters."""
        params = {
            "name": "${user_name}",
            "count": 10,
            "nested": {
                "value": "${nested_value}",
            },
        }
        variables = {
            "user_name": "Alice",
            "nested_value": "nested_data",
        }

        result = orchestrator._substitute_variables(params, variables)

        assert result["name"] == "Alice"
        assert result["count"] == 10
        assert result["nested"]["value"] == "nested_data"


class TestWorkflowTemplates:
    """Tests for workflow templates."""

    def test_email_triage_workflow(self):
        """Test email triage workflow creation."""
        workflow = EmailTriageWorkflow()

        assert workflow.id == "email_triage"
        assert workflow.workflow_type == WorkflowType.EMAIL_TRIAGE
        assert len(workflow.steps) >= 1

        # Check for categorize step
        step_names = [s.name for s in workflow.steps]
        assert "Categorize Emails" in step_names

    def test_report_generation_workflow(self):
        """Test report generation workflow creation."""
        workflow = ReportGenerationWorkflow()

        assert workflow.id == "report_generation"
        assert workflow.workflow_type == WorkflowType.REPORT_GENERATION
        assert len(workflow.steps) >= 1

        # Check that distribution requires approval
        distribute_step = next((s for s in workflow.steps if "Distribute" in s.name), None)
        if distribute_step:
            assert distribute_step.requires_approval is True

    def test_data_pipeline_workflow(self):
        """Test data pipeline workflow creation."""
        workflow = DataPipelineWorkflow()

        assert workflow.id == "data_pipeline"
        assert workflow.workflow_type == WorkflowType.DATA_PIPELINE
        assert len(workflow.steps) >= 4  # Ingest, validate, transform, export

    def test_get_template(self):
        """Test getting template by name."""
        workflow = get_template("email_triage")
        assert workflow is not None
        assert workflow.id == "email_triage"

        unknown = get_template("unknown_template")
        assert unknown is None

    def test_list_templates(self):
        """Test listing all templates."""
        templates = list_templates()

        assert len(templates) >= 3
        template_ids = [t["id"] for t in templates]
        assert "email_triage" in template_ids
        assert "report_generation" in template_ids
        assert "data_pipeline" in template_ids


class TestWorkflowExecution:
    """Tests for workflow execution."""

    @pytest.fixture
    def orchestrator(self):
        orch = WorkflowOrchestrator()
        # Register templates
        for template_name in ["email_triage", "report_generation", "data_pipeline"]:
            from workflow_agent.workflows.templates import WORKFLOW_TEMPLATES

            workflow = WORKFLOW_TEMPLATES[template_name]()
            orch.register_workflow(workflow)
        return orch

    @pytest.mark.asyncio
    async def test_execute_workflow_not_found(self, orchestrator):
        """Test error when workflow not found."""
        with pytest.raises(ValueError, match="not found"):
            await orchestrator.execute("nonexistent_workflow")

    @pytest.mark.asyncio
    async def test_cancel_execution(self, orchestrator):
        """Test cancelling an execution."""
        # Start an execution
        execution_id = "test_exec"

        orchestrator._active_executions[execution_id] = WorkflowResult(
            workflow_id=execution_id,
            status=WorkflowStatus.RUNNING,
        )

        result = await orchestrator.cancel_execution(execution_id)
        assert result is True
        assert orchestrator._active_executions[execution_id].status == WorkflowStatus.CANCELLED

    def test_callbacks(self, orchestrator):
        """Test setting callbacks."""

        def step_callback(w, s, r):
            return None

        def workflow_callback(w, r):
            return None

        def approval_callback(r):
            return None

        orchestrator.on_step_complete(step_callback)
        orchestrator.on_workflow_complete(workflow_callback)
        orchestrator.on_approval_required(approval_callback)

        assert orchestrator._on_step_complete == step_callback
        assert orchestrator._on_workflow_complete == workflow_callback
        assert orchestrator._on_approval_required == approval_callback

    @pytest.mark.asyncio
    async def test_execute_clears_active_executions_and_runs_sync_callbacks(self):
        """Completed workflows should not remain active and sync callbacks should work."""
        step_result = WorkflowResult(
            workflow_id="step_result",
            status=WorkflowStatus.COMPLETED,
            output={"done": True},
        )
        orchestrator = WorkflowOrchestrator(agent=StubAgent([step_result]))
        orchestrator.register_workflow(
            Workflow(
                id="single_step",
                name="Single Step",
                description="One step workflow",
                steps=[WorkflowStep(name="Run", action="Run", tool="test_tool")],
            )
        )
        callback_events = []

        orchestrator.on_step_complete(
            lambda workflow, step, result: callback_events.append(
                ("step", step.name, result.status)
            )
        )
        orchestrator.on_workflow_complete(
            lambda workflow, result: callback_events.append(("workflow", result.status))
        )

        result = await orchestrator.execute("single_step")

        assert result.status == WorkflowStatus.COMPLETED
        assert orchestrator.get_active_executions() == {}
        assert callback_events == [
            ("step", "Run", WorkflowStatus.COMPLETED),
            ("workflow", WorkflowStatus.COMPLETED),
        ]

    @pytest.mark.asyncio
    async def test_execute_stops_when_step_waits_for_approval(self):
        """Workflow execution should pause cleanly when a step needs approval."""

        class ApprovalStubAgent(StubAgent):
            async def process(self, task, context):
                self.pending_approvals = [
                    ApprovalRequest(
                        request_id="req-1",
                        tool_name="email_tool",
                        action_description="Send email",
                        proposed_input={"action": "send"},
                    )
                ]
                return WorkflowResult(
                    workflow_id="step_result",
                    status=WorkflowStatus.WAITING_APPROVAL,
                    output={"pending_approval": {"request_id": "req-1"}},
                )

        orchestrator = WorkflowOrchestrator(
            agent=ApprovalStubAgent([]),
            config=AgentConfig(auto_approve_safe_actions=False),
        )
        orchestrator.register_workflow(
            Workflow(
                id="approval_flow",
                name="Approval Flow",
                description="Workflow that pauses for approval",
                steps=[WorkflowStep(name="Send", action="Send", tool="email_tool")],
            )
        )
        notified_requests = []
        orchestrator.on_approval_required(
            lambda request: notified_requests.append(request.request_id)
        )

        result = await orchestrator.execute("approval_flow")

        assert result.status == WorkflowStatus.WAITING_APPROVAL
        assert result.errors == []
        assert result.approvals_requested == 1
        assert notified_requests == ["req-1"]
