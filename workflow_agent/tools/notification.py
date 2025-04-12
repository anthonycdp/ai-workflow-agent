"""
Notification tool for sending alerts and notifications.
"""

import json
from typing import Any, Optional
from datetime import datetime
from enum import Enum

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    """Available notification channels."""

    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    IN_APP = "in_app"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationInput(BaseModel):
    """Input schema for notification operations."""

    action: str = Field(
        description="Action to perform: 'send', 'schedule', 'list_channels', or 'history'"
    )
    channel: Optional[str] = Field(
        default="in_app", description="Notification channel: email, slack, webhook, sms, in_app"
    )
    recipient: Optional[str] = Field(
        default=None,
        description="Recipient (email address, slack channel, phone number, or user ID)",
    )
    subject: Optional[str] = Field(default=None, description="Notification subject/title")
    message: Optional[str] = Field(default=None, description="Notification body/message")
    priority: Optional[str] = Field(
        default="normal", description="Priority level: low, normal, high, urgent"
    )
    schedule_time: Optional[str] = Field(
        default=None, description="ISO datetime for scheduled delivery"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional metadata for the notification"
    )


class NotificationTool(BaseTool):
    """
    Tool for sending notifications through various channels.

    This tool provides capabilities for:
    - Send: Send a notification immediately
    - Schedule: Schedule a notification for later delivery (requires approval)
    - List Channels: Get available notification channels
    - History: View notification history

    Notifications can be sent through email, Slack, webhooks, SMS, or in-app.
    Scheduled notifications require human approval.
    """

    name: str = "notification"
    description: str = """Send notifications through various channels.

    Actions:
    - 'send': Send a notification immediately
    - 'schedule': Schedule a notification for later (REQUIRES APPROVAL)
    - 'list_channels': Get available notification channels
    - 'history': View recent notification history

    Channels: email, slack, webhook, sms, in_app
    Priority Levels: low, normal, high, urgent

    Sensitive Actions (require approval): schedule, sms, webhook
    """
    args_schema: type[BaseModel] = NotificationInput

    sensitive_actions: list[str] = ["schedule", "sms", "webhook"]

    # In-memory notification history for demo
    _notification_history: list[dict] = []

    def _run(
        self,
        action: str,
        channel: Optional[str] = "in_app",
        recipient: Optional[str] = None,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        priority: Optional[str] = "normal",
        schedule_time: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Synchronous run method."""
        import asyncio

        return asyncio.run(
            self._arun(
                action, channel, recipient, subject, message, priority, schedule_time, metadata
            )
        )

    async def _arun(
        self,
        action: str,
        channel: Optional[str] = "in_app",
        recipient: Optional[str] = None,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        priority: Optional[str] = "normal",
        schedule_time: Optional[str] = None,
        metadata: Optional[dict] = None,
        **kwargs,
    ) -> str:
        """Asynchronous run method."""

        if action == "send":
            return await self._send_notification(
                channel, recipient, subject, message, priority, metadata
            )
        elif action == "schedule":
            return await self._schedule_notification(
                channel, recipient, subject, message, priority, schedule_time, metadata
            )
        elif action == "list_channels":
            return await self._list_channels()
        elif action == "history":
            return await self._get_history()
        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}"})

    async def _send_notification(
        self,
        channel: Optional[str],
        recipient: Optional[str],
        subject: Optional[str],
        message: Optional[str],
        priority: Optional[str],
        metadata: Optional[dict],
    ) -> str:
        """Send a notification immediately."""
        if not message:
            return json.dumps({"success": False, "error": "Message is required"})

        notification_id = f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Validate channel
        valid_channels = ["email", "slack", "webhook", "sms", "in_app"]
        if channel not in valid_channels:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid channel. Must be one of: {', '.join(valid_channels)}",
                }
            )

        # Channel-specific validation
        if channel in ["email", "sms", "slack"] and not recipient:
            return json.dumps(
                {"success": False, "error": f"Recipient is required for {channel} channel"}
            )

        # Create notification record
        notification = {
            "id": notification_id,
            "channel": channel,
            "recipient": recipient,
            "subject": subject or "Notification",
            "message": message,
            "priority": priority,
            "status": "sent",
            "sent_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        # Add to history
        self._notification_history.append(notification)

        return json.dumps(
            {
                "success": True,
                "action": "send",
                "result": notification,
                "message": f"Notification sent via {channel}",
            },
            indent=2,
        )

    async def _schedule_notification(
        self,
        channel: Optional[str],
        recipient: Optional[str],
        subject: Optional[str],
        message: Optional[str],
        priority: Optional[str],
        schedule_time: Optional[str],
        metadata: Optional[dict],
    ) -> str:
        """Schedule a notification for later delivery (requires approval)."""
        if not message:
            return json.dumps({"success": False, "error": "Message is required"})

        if not schedule_time:
            return json.dumps(
                {"success": False, "error": "schedule_time is required for scheduled notifications"}
            )

        schedule_id = f"sched_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        return json.dumps(
            {
                "success": True,
                "action": "schedule",
                "requires_approval": True,
                "result": {
                    "schedule_id": schedule_id,
                    "channel": channel,
                    "recipient": recipient,
                    "subject": subject or "Scheduled Notification",
                    "message": message,
                    "priority": priority,
                    "scheduled_for": schedule_time,
                    "created_at": datetime.now().isoformat(),
                    "metadata": metadata or {},
                },
                "message": "Notification scheduled pending approval",
            },
            indent=2,
        )

    async def _list_channels(self) -> str:
        """List available notification channels."""
        channels = [
            {
                "id": "email",
                "name": "Email",
                "description": "Send notifications via email",
                "requires_recipient": True,
                "recipient_format": "email address",
                "supports_scheduling": True,
            },
            {
                "id": "slack",
                "name": "Slack",
                "description": "Post messages to Slack channels",
                "requires_recipient": True,
                "recipient_format": "channel ID or name",
                "supports_scheduling": True,
            },
            {
                "id": "webhook",
                "name": "Webhook",
                "description": "Send HTTP POST requests",
                "requires_recipient": True,
                "recipient_format": "URL",
                "supports_scheduling": True,
            },
            {
                "id": "sms",
                "name": "SMS",
                "description": "Send text messages",
                "requires_recipient": True,
                "recipient_format": "phone number",
                "supports_scheduling": True,
            },
            {
                "id": "in_app",
                "name": "In-App",
                "description": "Show notification in application",
                "requires_recipient": False,
                "recipient_format": "user ID (optional)",
                "supports_scheduling": False,
            },
        ]

        return json.dumps(
            {
                "success": True,
                "action": "list_channels",
                "result": {"channels": channels, "total": len(channels)},
            },
            indent=2,
        )

    async def _get_history(self) -> str:
        """Get notification history."""
        return json.dumps(
            {
                "success": True,
                "action": "history",
                "result": {
                    "notifications": self._notification_history[-20:],  # Last 20
                    "total": len(self._notification_history),
                },
            },
            indent=2,
        )
