"""
Human-in-the-loop approval middleware.

This middleware intercepts sensitive actions and requires human approval
before they can be executed.
"""

import uuid
from typing import Any, Optional
from abc import ABC, abstractmethod

from workflow_agent.models import ApprovalDecision, ApprovalRequest


class ApprovalHandler(ABC):
    """Abstract base class for approval handlers."""

    @abstractmethod
    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """
        Request approval from a human.

        Args:
            request: The approval request

        Returns:
            The decision made by the human
        """
        pass


class ConsoleApprovalHandler(ApprovalHandler):
    """Approval handler that uses console input."""

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Request approval via console."""
        print("\n" + "=" * 60)
        print("APPROVAL REQUIRED")
        print("=" * 60)
        print(f"Tool: {request.tool_name}")
        print(f"Action: {request.action_description}")
        print(f"Risk Level: {request.risk_level}")
        print("\nProposed Input:")
        for key, value in request.proposed_input.items():
            print(f"  {key}: {value}")
        print("\nOptions:")
        print("  [a] Approve")
        print("  [r] Reject")
        print("  [e] Edit and approve")
        print("  [d] Defer")
        print("=" * 60)

        while True:
            try:
                choice = input("Your decision [a/r/e/d]: ").strip().lower()
                if choice == "a":
                    return ApprovalDecision.APPROVE
                elif choice == "r":
                    return ApprovalDecision.REJECT
                elif choice == "e":
                    return ApprovalDecision.EDIT
                elif choice == "d":
                    return ApprovalDecision.DEFER
                else:
                    print("Invalid choice. Please enter a, r, e, or d.")
            except EOFError:
                # Non-interactive mode, auto-reject for safety
                return ApprovalDecision.REJECT


class HumanApprovalMiddleware:
    """
    Middleware for human-in-the-loop approval.

    This middleware intercepts tool calls that are marked as sensitive
    and requires human approval before execution.

    Features:
    - Configurable list of sensitive actions
    - Auto-approve safe actions
    - Custom approval handlers
    - Risk level assessment
    - Approval request queuing

    Attributes:
        auto_approve_safe: Whether to auto-approve non-sensitive actions
        sensitive_actions: List of action names that require approval
        approval_handler: Handler for approval requests
    """

    def __init__(
        self,
        auto_approve_safe: bool = True,
        sensitive_actions: Optional[list[str]] = None,
        approval_handler: Optional[ApprovalHandler] = None,
    ):
        """
        Initialize the human approval middleware.

        Args:
            auto_approve_safe: Auto-approve actions not in sensitive list
            sensitive_actions: List of action names requiring approval
            approval_handler: Custom approval handler (uses console if None)
        """
        self.auto_approve_safe = auto_approve_safe
        self.sensitive_actions = sensitive_actions or [
            "send_email",
            "send",
            "delete",
            "delete_data",
            "modify_settings",
            "external_api_call",
            "schedule",
            "webhook",
            "sms",
        ]
        self.approval_handler = approval_handler or ConsoleApprovalHandler()
        self._pending_requests: dict[str, ApprovalRequest] = {}

    def requires_approval(self, action_name: str, args: dict[str, Any]) -> bool:
        """
        Check if an action requires approval.

        Args:
            action_name: Name of the action/tool
            args: Arguments for the action

        Returns:
            True if approval is required
        """
        # Check if action is in sensitive list
        action_lower = action_name.lower()
        requested_action = str(args.get("action", "")).lower()
        for sensitive in self.sensitive_actions:
            sensitive_lower = sensitive.lower()
            if sensitive_lower in action_lower or sensitive_lower == requested_action:
                return True

        # If auto-approve is disabled, everything needs approval
        if not self.auto_approve_safe:
            return True

        return False

    def assess_risk_level(self, action_name: str, args: dict[str, Any]) -> str:
        """
        Assess the risk level of an action.

        Args:
            action_name: Name of the action
            args: Arguments for the action

        Returns:
            Risk level: "low", "medium", "high", or "critical"
        """
        action_target = f"{action_name.lower()} {str(args.get('action', '')).lower()}"

        # Critical actions
        critical_keywords = ["delete", "remove", "destroy", "drop"]
        if any(kw in action_target for kw in critical_keywords):
            return "critical"

        # High risk actions
        high_keywords = ["send", "email", "sms", "webhook", "external"]
        if any(kw in action_target for kw in high_keywords):
            return "high"

        # Medium risk actions
        medium_keywords = ["update", "modify", "change", "schedule"]
        if any(kw in action_target for kw in medium_keywords):
            return "medium"

        return "low"

    async def create_approval_request(
        self,
        action_name: str,
        args: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        Create an approval request for an action.

        Args:
            action_name: Name of the action
            args: Arguments for the action
            context: Additional context

        Returns:
            ApprovalRequest object
        """
        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            tool_name=action_name,
            action_description=f"Execute {action_name} with provided arguments",
            proposed_input=args,
            risk_level=self.assess_risk_level(action_name, args),
            context=context or {},
        )

        self._pending_requests[request.request_id] = request
        return request

    async def request_approval(
        self,
        request_id: str,
    ) -> ApprovalDecision:
        """
        Request approval for a pending request.

        Args:
            request_id: ID of the approval request

        Returns:
            The approval decision
        """
        request = self._pending_requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        decision = await self.approval_handler.request_approval(request)
        request.decision = decision
        return decision

    def apply_edit(
        self,
        request_id: str,
        modified_input: dict[str, Any],
    ) -> ApprovalRequest:
        """
        Apply edits to a pending request.

        Args:
            request_id: ID of the approval request
            modified_input: Modified input values

        Returns:
            Updated ApprovalRequest
        """
        request = self._pending_requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        request.modified_input = modified_input
        return request

    def get_pending_requests(self) -> list[ApprovalRequest]:
        """Get all pending approval requests."""
        return [req for req in self._pending_requests.values() if req.decision is None]

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a specific approval request."""
        return self._pending_requests.get(request_id)

    def clear_request(self, request_id: str) -> None:
        """Remove a request from the pending queue."""
        self._pending_requests.pop(request_id, None)

    def add_sensitive_action(self, action_name: str) -> None:
        """Add an action to the sensitive list."""
        if action_name not in self.sensitive_actions:
            self.sensitive_actions.append(action_name)

    def remove_sensitive_action(self, action_name: str) -> None:
        """Remove an action from the sensitive list."""
        if action_name in self.sensitive_actions:
            self.sensitive_actions.remove(action_name)
