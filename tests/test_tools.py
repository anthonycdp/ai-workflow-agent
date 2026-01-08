"""
Tests for AI Workflow Agent tools.
"""

import pytest
import json

from workflow_agent.tools.email import EmailTool
from workflow_agent.tools.report import ReportGeneratorTool
from workflow_agent.tools.data import DataProcessingTool
from workflow_agent.tools.notification import NotificationTool


class TestEmailTool:
    """Tests for the EmailTool."""

    @pytest.fixture
    def tool(self):
        return EmailTool()

    @pytest.mark.asyncio
    async def test_triage_emails(self, tool):
        """Test email triage functionality."""
        emails = [
            {
                "id": "1",
                "sender": "boss@company.com",
                "subject": "URGENT: Meeting tomorrow",
                "body": "Please confirm your attendance",
            },
            {
                "id": "2",
                "sender": "newsletter@marketing.com",
                "subject": "Weekly Newsletter",
                "body": "This is your weekly update",
            },
        ]

        result = await tool._arun(action="triage", emails=emails)
        data = json.loads(result)

        assert data["success"] is True
        assert data["action"] == "triage"
        assert data["summary"]["total_emails"] == 2
        assert data["summary"]["urgent"] >= 1

    @pytest.mark.asyncio
    async def test_draft_email(self, tool):
        """Test email drafting."""
        result = await tool._arun(
            action="draft",
            to="test@example.com",
            subject="Test Subject",
            body="Test body content",
        )
        data = json.loads(result)

        assert data["success"] is True
        assert data["result"]["to"] == "test@example.com"
        assert data["result"]["subject"] == "Test Subject"

    @pytest.mark.asyncio
    async def test_draft_email_missing_recipient(self, tool):
        """Test draft fails without recipient."""
        result = await tool._arun(action="draft", subject="Test")
        data = json.loads(result)

        assert data["success"] is False
        assert "Recipient" in data["error"]

    @pytest.mark.asyncio
    async def test_categorize_emails(self, tool):
        """Test email categorization."""
        emails = [
            {"id": "1", "sender": "work@company.com", "subject": "Project update"},
            {"id": "2", "sender": "deals@store.com", "subject": "50% OFF SALE!"},
        ]

        result = await tool._arun(action="categorize", emails=emails)
        data = json.loads(result)

        assert data["success"] is True
        assert "categories" in str(data).lower() or "result" in data

    def test_determine_priority(self, tool):
        """Test priority determination."""
        from workflow_agent.models import Priority

        urgent_email = {"subject": "URGENT deadline", "body": ""}
        priority = tool._determine_priority(urgent_email)
        assert priority == Priority.URGENT

        low_email = {"subject": "Weekly newsletter", "body": "FYI"}
        priority = tool._determine_priority(low_email)
        assert priority == Priority.LOW


class TestReportGeneratorTool:
    """Tests for the ReportGeneratorTool."""

    @pytest.fixture
    def tool(self):
        return ReportGeneratorTool()

    @pytest.mark.asyncio
    async def test_generate_report(self, tool):
        """Test report generation."""
        result = await tool._arun(
            action="generate",
            report_type="summary",
            title="Test Report",
            data={"key": "value"},
            format="markdown",
        )
        data = json.loads(result)

        assert data["success"] is True
        assert data["result"]["title"] == "Test Report"
        assert data["result"]["format"] == "markdown"

    @pytest.mark.asyncio
    async def test_generate_report_missing_data(self, tool):
        """Test report generation fails without data."""
        result = await tool._arun(
            action="generate",
            report_type="summary",
            title="Test Report",
        )
        data = json.loads(result)

        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_list_templates(self, tool):
        """Test listing report templates."""
        result = await tool._arun(action="list_templates")
        data = json.loads(result)

        assert data["success"] is True
        assert data["result"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_preview_report(self, tool):
        """Test report preview."""
        result = await tool._arun(
            action="preview",
            report_type="summary",
            data={"sample": "data"},
        )
        data = json.loads(result)

        assert data["success"] is True
        assert "preview" in data["result"]


class TestDataProcessingTool:
    """Tests for the DataProcessingTool."""

    @pytest.fixture
    def tool(self):
        return DataProcessingTool()

    @pytest.mark.asyncio
    async def test_filter_data(self, tool):
        """Test data filtering."""
        data = [
            {"id": 1, "status": "active"},
            {"id": 2, "status": "inactive"},
            {"id": 3, "status": "active"},
        ]

        result = await tool._arun(
            action="transform",
            transform_type="filter",
            data=data,
            parameters={"conditions": [{"field": "status", "operator": "eq", "value": "active"}]},
        )
        output = json.loads(result)

        assert output["success"] is True
        assert output["result"]["original_count"] == 3

    @pytest.mark.asyncio
    async def test_validate_data(self, tool):
        """Test data validation."""
        data = [
            {"id": 1, "name": "Test"},
            {"id": 2, "name": None},  # Missing name
        ]

        result = await tool._arun(
            action="validate",
            data=data,
            parameters={"required_fields": ["id", "name"]},
        )
        output = json.loads(result)

        assert output["success"] is True
        assert output["result"]["errors_count"] >= 1

    @pytest.mark.asyncio
    async def test_analyze_data(self, tool):
        """Test data analysis."""
        data = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 200},
        ]

        result = await tool._arun(action="analyze", data=data)
        output = json.loads(result)

        assert output["success"] is True
        assert output["result"]["total_records"] == 2
        assert "field_statistics" in output["result"]


class TestNotificationTool:
    """Tests for the NotificationTool."""

    @pytest.fixture
    def tool(self):
        return NotificationTool()

    @pytest.mark.asyncio
    async def test_send_notification(self, tool):
        """Test sending notification."""
        result = await tool._arun(
            action="send",
            channel="in_app",
            subject="Test Notification",
            message="This is a test",
            priority="normal",
        )
        data = json.loads(result)

        assert data["success"] is True
        assert data["result"]["subject"] == "Test Notification"

    @pytest.mark.asyncio
    async def test_send_notification_missing_message(self, tool):
        """Test notification fails without message."""
        result = await tool._arun(action="send", channel="in_app")
        data = json.loads(result)

        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_list_channels(self, tool):
        """Test listing channels."""
        result = await tool._arun(action="list_channels")
        data = json.loads(result)

        assert data["success"] is True
        assert data["result"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_history(self, tool):
        """Test notification history."""
        # First send a notification
        await tool._arun(
            action="send",
            channel="in_app",
            message="Test",
        )

        # Then check history
        result = await tool._arun(action="history")
        data = json.loads(result)

        assert data["success"] is True
        assert "notifications" in data["result"]
