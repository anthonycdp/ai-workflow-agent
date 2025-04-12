"""
Email tool for triage, drafting, and sending emails.
"""

import json
from typing import Any, Optional
from datetime import datetime

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from workflow_agent.models import Email, Priority


class EmailInput(BaseModel):
    """Input schema for email operations."""

    action: str = Field(
        description="Action to perform: 'triage', 'draft', 'send', 'categorize', or 'summarize'"
    )
    emails: Optional[list[dict[str, Any]]] = Field(
        default=None, description="List of emails to process (for triage/categorize)"
    )
    to: Optional[str] = Field(default=None, description="Recipient email address (for draft/send)")
    subject: Optional[str] = Field(default=None, description="Email subject (for draft/send)")
    body: Optional[str] = Field(default=None, description="Email body content (for draft/send)")
    email_id: Optional[str] = Field(default=None, description="Specific email ID to process")
    filters: Optional[dict[str, Any]] = Field(
        default=None, description="Filters for email triage (priority, sender, date_range)"
    )


class EmailTool(BaseTool):
    """
    Tool for email triage and management.

    This tool provides capabilities for:
    - Triage: Analyze and prioritize incoming emails
    - Draft: Create email drafts with suggested content
    - Send: Send emails (requires human approval)
    - Categorize: Sort emails into categories
    - Summarize: Generate summaries of email threads

    The 'send' action is marked as sensitive and requires human approval.
    """

    name: str = "email_tool"
    description: str = """Manage email workflows including triage, drafting, sending, and summarization.

    Actions:
    - 'triage': Analyze emails and prioritize based on urgency
    - 'draft': Create an email draft for review
    - 'send': Send an email (REQUIRES APPROVAL)
    - 'categorize': Sort emails into categories
    - 'summarize': Generate a summary of emails

    Sensitive Actions (require approval): send
    """
    args_schema: type[BaseModel] = EmailInput

    # Mark send as sensitive
    sensitive_actions: list[str] = ["send"]

    def _run(
        self,
        action: str,
        emails: Optional[list[dict]] = None,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        email_id: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> str:
        """Synchronous run method."""
        import asyncio

        return asyncio.run(self._arun(action, emails, to, subject, body, email_id, filters))

    async def _arun(
        self,
        action: str,
        emails: Optional[list[dict]] = None,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        email_id: Optional[str] = None,
        filters: Optional[dict] = None,
        **kwargs,
    ) -> str:
        """Asynchronous run method."""

        if action == "triage":
            return await self._triage_emails(emails or [], filters)
        elif action == "draft":
            return await self._draft_email(to, subject, body)
        elif action == "send":
            return await self._send_email(to, subject, body)
        elif action == "categorize":
            return await self._categorize_emails(emails or [])
        elif action == "summarize":
            return await self._summarize_emails(emails or [])
        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}"})

    async def _triage_emails(self, emails: list[dict], filters: Optional[dict] = None) -> str:
        """
        Triage emails based on priority and content.

        Args:
            emails: List of email dictionaries
            filters: Optional filters for triage

        Returns:
            JSON string with triage results
        """
        triaged: dict[str, list[dict[str, Any]]] = {
            "urgent": [],
            "high": [],
            "medium": [],
            "low": [],
            "requires_action": [],
            "can_defer": [],
        }

        for email_data in emails:
            # Analyze email for priority
            priority = self._determine_priority(email_data)
            requires_action = self._check_action_required(email_data)

            email_obj = Email(
                id=email_data.get("id", str(len(emails))),
                sender=email_data.get("sender", "unknown"),
                subject=email_data.get("subject", ""),
                body=email_data.get("body", ""),
                priority=priority,
                action_required=requires_action,
            )

            priority_key = priority.value if isinstance(priority, Priority) else priority
            triaged[priority_key].append(email_obj.model_dump(mode="json"))

            if requires_action:
                triaged["requires_action"].append(email_obj.model_dump(mode="json"))
            else:
                triaged["can_defer"].append(email_obj.model_dump(mode="json"))

        # Apply filters if provided
        if filters:
            if "min_priority" in filters:
                priority_order = ["urgent", "high", "medium", "low"]
                min_idx = priority_order.index(filters["min_priority"])
                for p in priority_order[min_idx + 1 :]:
                    triaged[p] = []

        return json.dumps(
            {
                "success": True,
                "action": "triage",
                "result": triaged,
                "summary": {
                    "total_emails": len(emails),
                    "urgent": len(triaged["urgent"]),
                    "high": len(triaged["high"]),
                    "medium": len(triaged["medium"]),
                    "low": len(triaged["low"]),
                    "requires_action": len(triaged["requires_action"]),
                },
            },
            indent=2,
        )

    async def _draft_email(
        self, to: Optional[str], subject: Optional[str], body: Optional[str]
    ) -> str:
        """
        Create an email draft.

        Args:
            to: Recipient address
            subject: Email subject
            body: Email body

        Returns:
            JSON string with draft details
        """
        if not to:
            return json.dumps({"success": False, "error": "Recipient 'to' address is required"})

        draft = {
            "id": f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "to": to,
            "subject": subject or "(No Subject)",
            "body": body or "",
            "status": "draft",
            "created_at": datetime.now().isoformat(),
        }

        return json.dumps(
            {
                "success": True,
                "action": "draft",
                "result": draft,
                "message": f"Draft created for {to}. Review before sending.",
            },
            indent=2,
        )

    async def _send_email(
        self, to: Optional[str], subject: Optional[str], body: Optional[str]
    ) -> str:
        """
        Send an email (simulated).

        In a real implementation, this would connect to an SMTP server.
        This is marked as a sensitive action requiring approval.

        Args:
            to: Recipient address
            subject: Email subject
            body: Email body

        Returns:
            JSON string with send result
        """
        if not to or not subject or not body:
            return json.dumps(
                {
                    "success": False,
                    "error": "Missing required fields: to, subject, and body are required",
                }
            )

        # Simulate sending
        result = {
            "message_id": f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "to": to,
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            "status": "sent",
        }

        return json.dumps(
            {
                "success": True,
                "action": "send",
                "result": result,
                "message": f"Email sent successfully to {to}",
            },
            indent=2,
        )

    async def _categorize_emails(self, emails: list[dict]) -> str:
        """
        Categorize emails into predefined categories.

        Args:
            emails: List of email dictionaries

        Returns:
            JSON string with categorization results
        """
        categories: dict[str, list[dict[str, Any]]] = {
            "work": [],
            "personal": [],
            "promotional": [],
            "notifications": [],
            "spam": [],
            "uncategorized": [],
        }

        for email_data in emails:
            category = self._determine_category(email_data)
            categories[category].append(
                {
                    "id": email_data.get("id"),
                    "sender": email_data.get("sender"),
                    "subject": email_data.get("subject"),
                }
            )

        return json.dumps(
            {
                "success": True,
                "action": "categorize",
                "result": categories,
                "summary": {"total": len(emails), **{k: len(v) for k, v in categories.items()}},
            },
            indent=2,
        )

    async def _summarize_emails(self, emails: list[dict]) -> str:
        """
        Generate a summary of emails.

        Args:
            emails: List of email dictionaries

        Returns:
            JSON string with summary
        """
        if not emails:
            return json.dumps(
                {
                    "success": True,
                    "action": "summarize",
                    "result": {"summary": "No emails to summarize"},
                }
            )

        # Generate summary statistics
        senders = set(e.get("sender", "unknown") for e in emails)
        subjects = [e.get("subject", "") for e in emails]

        summary = {
            "total_emails": len(emails),
            "unique_senders": len(senders),
            "top_senders": list(senders)[:5],
            "subjects": subjects,
            "generated_at": datetime.now().isoformat(),
        }

        return json.dumps({"success": True, "action": "summarize", "result": summary}, indent=2)

    def _determine_priority(self, email: dict) -> Priority:
        """Determine email priority based on content analysis."""
        subject = email.get("subject", "").lower()
        body = email.get("body", "").lower()
        combined = f"{subject} {body}"

        urgent_keywords = ["urgent", "asap", "critical", "emergency", "immediately"]
        high_keywords = ["important", "priority", "deadline", "due today", "action required"]
        low_keywords = ["fyi", "newsletter", "update", "weekly", "monthly"]

        if any(kw in combined for kw in urgent_keywords):
            return Priority.URGENT
        elif any(kw in combined for kw in high_keywords):
            return Priority.HIGH
        elif any(kw in combined for kw in low_keywords):
            return Priority.LOW
        else:
            return Priority.MEDIUM

    def _check_action_required(self, email: dict) -> bool:
        """Check if email requires action."""
        subject = email.get("subject", "").lower()
        body = email.get("body", "").lower()
        combined = f"{subject} {body}"

        action_keywords = [
            "please reply",
            "response required",
            "action needed",
            "confirm",
            "approve",
            "review",
            "sign",
            "complete",
        ]

        return any(kw in combined for kw in action_keywords)

    def _determine_category(self, email: dict) -> str:
        """Determine email category."""
        subject = email.get("subject", "").lower()
        sender = email.get("sender", "").lower()
        combined = f"{subject} {sender}"

        if any(kw in combined for kw in ["sale", "discount", "offer", "deal"]):
            return "promotional"
        elif any(kw in combined for kw in ["notification", "alert", "update"]):
            return "notifications"
        elif any(kw in combined for kw in ["spam", "winner", "click here"]):
            return "spam"
        elif any(kw in combined for kw in ["work", "office", "meeting", "project"]):
            return "work"
        elif any(kw in combined for kw in ["personal", "family", "friend"]):
            return "personal"
        else:
            return "uncategorized"
