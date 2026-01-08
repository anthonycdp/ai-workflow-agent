"""
Basic usage example for the AI Workflow Agent.

This example demonstrates:
- Creating and configuring the agent
- Registering tools
- Processing tasks
- Handling results
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow_agent.agent import WorkflowAgent
from workflow_agent.config import AgentConfig
from workflow_agent.tools import (
    EmailTool,
    ReportGeneratorTool,
    DataProcessingTool,
    NotificationTool,
)


async def main():
    """Run basic usage example."""
    print("=" * 60)
    print("AI Workflow Agent - Basic Usage Example")
    print("=" * 60)

    # 1. Create agent configuration
    print("\n1. Creating agent configuration...")
    config = AgentConfig(
        llm_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        temperature=0.7,
        auto_approve_safe_actions=True,
        enable_fallback=True,
    )

    # 2. Create the agent
    print("2. Initializing agent...")
    agent = WorkflowAgent(config=config)

    # 3. Register tools
    print("3. Registering tools...")
    agent.register_tool(EmailTool())
    agent.register_tool(ReportGeneratorTool())
    agent.register_tool(DataProcessingTool())
    agent.register_tool(NotificationTool())

    print(f"   Registered {len(agent.tools)} tools: {list(agent.tools.keys())}")

    # 4. Process sample emails
    print("\n4. Processing sample emails...")

    sample_emails = [
        {
            "id": "email_001",
            "sender": "boss@company.com",
            "subject": "URGENT: Q4 Budget Review Meeting Tomorrow",
            "body": "Please confirm your availability for the Q4 budget review meeting tomorrow at 2 PM. Your input is required.",
        },
        {
            "id": "email_002",
            "sender": "newsletter@tech-weekly.com",
            "subject": "This Week in Tech: AI Breakthroughs",
            "body": "Here's your weekly roundup of the latest in technology...",
        },
        {
            "id": "email_003",
            "sender": "hr@company.com",
            "subject": "Action Required: Update Emergency Contact Information",
            "body": "Please update your emergency contact information in the HR portal by Friday.",
        },
    ]

    # Use the email tool directly
    email_tool = agent.tools["email_tool"]

    # Triage emails
    triage_result = await email_tool._arun(
        action="triage",
        emails=sample_emails,
    )
    print("\n   Email Triage Results:")
    import json

    triage_data = json.loads(triage_result)
    print(f"   - Total emails: {triage_data['summary']['total_emails']}")
    print(f"   - Urgent: {triage_data['summary']['urgent']}")
    print(f"   - Requires action: {triage_data['summary']['requires_action']}")

    # Categorize emails
    categorize_result = await email_tool._arun(
        action="categorize",
        emails=sample_emails,
    )
    print("\n   Email Categories:")
    cat_data = json.loads(categorize_result)
    for category, count in cat_data["summary"].items():
        if category != "total" and count > 0:
            print(f"   - {category}: {count}")

    # 5. Generate a report
    print("\n5. Generating a sample report...")

    report_tool = agent.tools["report_generator"]
    report_result = await report_tool._arun(
        action="generate",
        report_type="summary",
        title="Weekly Email Triage Report",
        data={
            "emails_processed": len(sample_emails),
            "categories": cat_data["summary"],
            "priority_breakdown": triage_data["summary"],
        },
        format="markdown",
    )

    report_data = json.loads(report_result)
    print(f"   Report ID: {report_data['result']['report_id']}")
    print(f"   Format: {report_data['result']['format']}")

    # 6. Process some data
    print("\n6. Processing sample data...")

    data_tool = agent.tools["data_processor"]
    sample_data = [
        {"id": 1, "name": "Alice", "department": "Engineering", "salary": 100000},
        {"id": 2, "name": "Bob", "department": "Marketing", "salary": 80000},
        {"id": 3, "name": "Charlie", "department": "Engineering", "salary": 95000},
        {"id": 4, "name": "Diana", "department": "Sales", "salary": 85000},
    ]

    analyze_result = await data_tool._arun(
        action="analyze",
        data=sample_data,
    )
    analyze_data = json.loads(analyze_result)
    print(f"   Records analyzed: {analyze_data['result']['total_records']}")
    print(f"   Fields detected: {analyze_data['result']['total_fields']}")
    print(f"   Data quality: {analyze_data['result']['data_quality']['completeness']:.2%}")

    # 7. Send notification
    print("\n7. Sending completion notification...")

    notification_tool = agent.tools["notification"]
    notify_result = await notification_tool._arun(
        action="send",
        channel="in_app",
        subject="Workflow Example Completed",
        message="The basic usage example has completed successfully!",
        priority="normal",
    )
    notify_data = json.loads(notify_result)
    print(f"   Notification sent: {notify_data['success']}")

    # 8. Summary
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("- Tools can be used directly or through the agent")
    print("- Each tool returns JSON-formatted results")
    print("- The agent provides reasoning and orchestration")
    print("- Middleware handles retries and approvals")


if __name__ == "__main__":
    asyncio.run(main())
