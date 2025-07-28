"""
Predefined workflow templates for common use cases.

These templates provide ready-to-use workflows for:
- Email triage and management
- Report generation
- Data processing pipelines
"""

from typing import Optional

from workflow_agent.workflows.orchestrator import (
    Workflow,
    WorkflowStep,
    WorkflowType,
)


def EmailTriageWorkflow() -> Workflow:
    """
    Create an email triage workflow.

    This workflow:
    1. Fetches and categorizes incoming emails
    2. Prioritizes based on content analysis
    3. Drafts responses for action-required emails
    4. Sends notifications for urgent items

    Returns:
        Configured Workflow for email triage
    """
    return Workflow(
        id="email_triage",
        name="Email Triage",
        description="Automatically triage and manage incoming emails",
        workflow_type=WorkflowType.EMAIL_TRIAGE,
        steps=[
            WorkflowStep(
                name="Categorize Emails",
                action="Categorize all incoming emails into predefined categories",
                tool="email_tool",
                parameters={
                    "action": "categorize",
                },
                requires_approval=False,
                on_failure="continue",
            ),
            WorkflowStep(
                name="Prioritize Emails",
                action="Prioritize emails based on urgency and importance",
                tool="email_tool",
                parameters={
                    "action": "triage",
                },
                requires_approval=False,
                on_failure="continue",
            ),
            WorkflowStep(
                name="Draft Responses",
                action="Draft responses for emails requiring action",
                tool="email_tool",
                parameters={
                    "action": "draft",
                },
                requires_approval=False,
                on_failure="skip",
            ),
            WorkflowStep(
                name="Notify Urgent Items",
                action="Send notifications for urgent emails",
                tool="notification",
                parameters={
                    "action": "send",
                    "priority": "high",
                },
                requires_approval=True,
                on_failure="skip",
            ),
        ],
        metadata={
            "estimated_time": "2-5 minutes",
            "requires_approval_for": ["Notify Urgent Items"],
        },
    )


def ReportGenerationWorkflow() -> Workflow:
    """
    Create a report generation workflow.

    This workflow:
    1. Collects data from specified sources
    2. Processes and analyzes the data
    3. Generates a formatted report
    4. Distributes to recipients

    Returns:
        Configured Workflow for report generation
    """
    return Workflow(
        id="report_generation",
        name="Report Generation",
        description="Generate and distribute automated reports",
        workflow_type=WorkflowType.REPORT_GENERATION,
        steps=[
            WorkflowStep(
                name="Fetch Data",
                action="Fetch data from specified sources",
                tool="data_processor",
                parameters={
                    "action": "analyze",
                    "source": "${data_source}",
                },
                requires_approval=False,
                on_failure="abort",
            ),
            WorkflowStep(
                name="Process Data",
                action="Process and transform the collected data",
                tool="data_processor",
                parameters={
                    "action": "transform",
                    "transform_type": "normalize",
                },
                requires_approval=False,
                on_failure="retry",
            ),
            WorkflowStep(
                name="Generate Report",
                action="Generate the formatted report",
                tool="report_generator",
                parameters={
                    "action": "generate",
                    "report_type": "${report_type}",
                    "title": "${report_title}",
                    "format": "${format}",
                },
                requires_approval=False,
                on_failure="retry",
            ),
            WorkflowStep(
                name="Distribute Report",
                action="Send report to recipients",
                tool="email_tool",
                parameters={
                    "action": "send",
                    "to": "${recipients}",
                    "subject": "${report_title}",
                },
                requires_approval=True,
                on_failure="skip",
            ),
        ],
        metadata={
            "estimated_time": "5-15 minutes",
            "requires_approval_for": ["Distribute Report"],
            "supports_scheduling": True,
        },
    )


def DataPipelineWorkflow() -> Workflow:
    """
    Create a data processing pipeline workflow.

    This workflow:
    1. Ingests data from source
    2. Validates data quality
    3. Transforms and enriches data
    4. Exports to destination

    Returns:
        Configured Workflow for data pipeline
    """
    return Workflow(
        id="data_pipeline",
        name="Data Processing Pipeline",
        description="ETL pipeline for data processing and transformation",
        workflow_type=WorkflowType.DATA_PIPELINE,
        steps=[
            WorkflowStep(
                name="Ingest Data",
                action="Ingest raw data from source",
                tool="data_processor",
                parameters={
                    "action": "analyze",
                    "source": "${source}",
                },
                requires_approval=False,
                on_failure="abort",
            ),
            WorkflowStep(
                name="Validate Data",
                action="Validate data quality and integrity",
                tool="data_processor",
                parameters={
                    "action": "validate",
                    "parameters": {
                        "required_fields": ["id", "timestamp", "value"],
                    },
                },
                requires_approval=False,
                on_failure="continue",
            ),
            WorkflowStep(
                name="Transform Data",
                action="Apply transformations to data",
                tool="data_processor",
                parameters={
                    "action": "transform",
                    "transform_type": "${transform_type}",
                    "parameters": "${transform_params}",
                },
                requires_approval=False,
                on_failure="retry",
            ),
            WorkflowStep(
                name="Enrich Data",
                action="Enrich data with additional information",
                tool="data_processor",
                parameters={
                    "action": "merge",
                    "parameters": {
                        "strategy": "dedupe",
                    },
                },
                requires_approval=False,
                on_failure="skip",
            ),
            WorkflowStep(
                name="Export Data",
                action="Export processed data to destination",
                tool="data_processor",
                parameters={
                    "action": "export",
                    "output_format": "${output_format}",
                    "source": "${destination}",
                },
                requires_approval=False,
                on_failure="retry",
            ),
            WorkflowStep(
                name="Notify Completion",
                action="Send completion notification",
                tool="notification",
                parameters={
                    "action": "send",
                    "priority": "normal",
                },
                requires_approval=False,
                on_failure="skip",
            ),
        ],
        metadata={
            "estimated_time": "10-30 minutes",
            "supports_batch_processing": True,
            "supports_scheduling": True,
        },
    )


# All available templates
WORKFLOW_TEMPLATES = {
    "email_triage": EmailTriageWorkflow,
    "report_generation": ReportGenerationWorkflow,
    "data_pipeline": DataPipelineWorkflow,
}


def get_template(template_name: str) -> Optional[Workflow]:
    """
    Get a workflow template by name.

    Args:
        template_name: Name of the template

    Returns:
        Workflow instance or None if not found
    """
    template_func = WORKFLOW_TEMPLATES.get(template_name)
    if template_func:
        return template_func()
    return None


def list_templates() -> list[dict[str, str]]:
    """List all available workflow templates."""
    return [
        {
            "id": "email_triage",
            "name": "Email Triage",
            "description": "Automatically triage and manage incoming emails",
        },
        {
            "id": "report_generation",
            "name": "Report Generation",
            "description": "Generate and distribute automated reports",
        },
        {
            "id": "data_pipeline",
            "name": "Data Processing Pipeline",
            "description": "ETL pipeline for data processing and transformation",
        },
    ]
