"""
Workflow orchestration example for the AI Workflow Agent.

This example demonstrates:
- Creating custom workflows
- Using the workflow orchestrator
- Executing predefined templates
- Handling workflow results
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow_agent.agent import WorkflowAgent
from workflow_agent.config import AgentConfig
from workflow_agent.tools import (
    EmailTool,
    ReportGeneratorTool,
    DataProcessingTool,
    NotificationTool,
)
from workflow_agent.workflows import WorkflowOrchestrator
from workflow_agent.workflows.templates import (
    EmailTriageWorkflow,
    ReportGenerationWorkflow,
    DataPipelineWorkflow,
    list_templates,
)
from workflow_agent.workflows.orchestrator import WorkflowType


async def main():
    """Run workflow orchestration example."""
    print("=" * 70)
    print("AI Workflow Agent - Workflow Orchestration Example")
    print("=" * 70)

    # 1. Set up the orchestrator
    print("\n1. Setting up Workflow Orchestrator...")

    config = AgentConfig(
        auto_approve_safe_actions=True,
        enable_fallback=True,
    )

    agent = WorkflowAgent(config=config)
    agent.register_tool(EmailTool())
    agent.register_tool(ReportGeneratorTool())
    agent.register_tool(DataProcessingTool())
    agent.register_tool(NotificationTool())

    orchestrator = WorkflowOrchestrator(agent=agent, config=config)

    # 2. Register predefined workflows
    print("2. Registering predefined workflows...")
    orchestrator.register_workflow(EmailTriageWorkflow())
    orchestrator.register_workflow(ReportGenerationWorkflow())
    orchestrator.register_workflow(DataPipelineWorkflow())

    print("   Available workflows:")
    for wf in orchestrator.list_workflows():
        print(f"   - {wf.id}: {wf.description[:50]}...")

    # 3. Create a custom workflow
    print("\n3. Creating a custom workflow...")

    custom_workflow = orchestrator.create_workflow(
        name="Custom Data Report",
        description="Process data and generate a customized report",
        steps=[
            {
                "name": "Analyze Data",
                "action": "Analyze the input data for statistics",
                "tool": "data_processor",
                "parameters": {"action": "analyze"},
                "on_failure": "abort",
            },
            {
                "name": "Transform Data",
                "action": "Normalize and clean the data",
                "tool": "data_processor",
                "parameters": {
                    "action": "transform",
                    "transform_type": "normalize",
                },
                "on_failure": "retry",
            },
            {
                "name": "Generate Report",
                "action": "Create a summary report",
                "tool": "report_generator",
                "parameters": {
                    "action": "generate",
                    "report_type": "summary",
                    "format": "markdown",
                },
                "on_failure": "skip",
            },
            {
                "name": "Send Notification",
                "action": "Notify about completion",
                "tool": "notification",
                "parameters": {
                    "action": "send",
                    "channel": "in_app",
                    "priority": "normal",
                },
                "requires_approval": False,
                "on_failure": "skip",
            },
        ],
        workflow_type=WorkflowType.CUSTOM,
    )

    print(f"   Created workflow: {custom_workflow.id}")
    print(f"   Steps: {len(custom_workflow.steps)}")

    # 4. List all templates
    print("\n4. Available workflow templates:")
    templates = list_templates()
    for t in templates:
        print(f"   [{t['id']}] {t['name']}: {t['description']}")

    # 5. Demonstrate workflow step details
    print("\n5. Workflow step details (Email Triage):")
    email_workflow = orchestrator.get_workflow("email_triage")
    for i, step in enumerate(email_workflow.steps, 1):
        approval_marker = " [REQUIRES APPROVAL]" if step.requires_approval else ""
        print(f"   Step {i}: {step.name}{approval_marker}")
        print(f"           Tool: {step.tool}")
        print(f"           On Failure: {step.on_failure}")

    # 6. Simulate workflow execution (without actual LLM calls)
    print("\n6. Workflow execution simulation...")
    print("   (Note: Full execution requires LLM API keys)")

    # Show what variables would be substituted
    print("\n   Variable substitution example:")
    variables = {
        "data_source": "sales_database",
        "report_type": "detailed",
        "report_title": "Monthly Sales Report",
        "format": "html",
    }
    params = {
        "source": "${data_source}",
        "report_type": "${report_type}",
        "title": "${report_title}",
    }
    substituted = orchestrator._substitute_variables(params, variables)
    print(f"   Original: {params}")
    print(f"   Variables: {variables}")
    print(f"   Result: {substituted}")

    # 7. Show middleware integration
    print("\n7. Middleware integration:")
    print(f"   - Retry middleware: max {config.max_retries} retries")
    print(f"   - Auto-approve safe: {config.auto_approve_safe_actions}")
    print(f"   - Fallback enabled: {config.enable_fallback}")
    print(f"   - Sensitive actions: {config.sensitive_actions}")

    # 8. Summary
    print("\n" + "=" * 70)
    print("Workflow Orchestration Example Complete!")
    print("=" * 70)
    print("\nKey Concepts Demonstrated:")
    print("1. Workflow templates provide ready-to-use automation")
    print("2. Custom workflows can be created for specific needs")
    print("3. Steps have configurable failure handling")
    print("4. Variable substitution enables dynamic parameters")
    print("5. Middleware provides safety and resilience")


if __name__ == "__main__":
    asyncio.run(main())
