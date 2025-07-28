"""
Fallback middleware for graceful degradation.

This middleware provides fallback mechanisms when tools fail,
including alternative actions, default values, and recovery strategies.
"""

import json
from typing import Any, Optional
from datetime import datetime
from enum import Enum


class FallbackStrategy(str, Enum):
    """Available fallback strategies."""

    DEFAULT_VALUE = "default_value"  # Return a default value
    ALTERNATIVE_TOOL = "alternative_tool"  # Use a different tool
    SIMPLIFIED = "simplified"  # Use a simplified version
    SKIP = "skip"  # Skip the failed step
    ABORT = "abort"  # Abort the workflow
    RETRY_LATER = "retry_later"  # Queue for later retry


class FallbackMiddleware:
    """
    Middleware for handling failures with fallback mechanisms.

    This middleware provides multiple strategies for graceful
    degradation when tool executions fail.

    Features:
    - Multiple fallback strategies
    - Configurable per-action fallbacks
    - Fallback logging and tracking
    - Recovery notifications

    Attributes:
        enabled: Whether fallback is enabled
        default_strategy: Default fallback strategy
        fallbacks: Per-action fallback configurations
    """

    def __init__(
        self,
        enabled: bool = True,
        default_strategy: FallbackStrategy = FallbackStrategy.DEFAULT_VALUE,
        fallbacks: Optional[dict[str, dict[str, Any]]] = None,
    ):
        """
        Initialize the fallback middleware.

        Args:
            enabled: Whether fallback is enabled
            default_strategy: Default strategy when no specific fallback
            fallbacks: Dictionary of action-specific fallback configs
        """
        self.enabled = enabled
        self.default_strategy = default_strategy
        self.fallbacks = fallbacks or {}

        # Fallback history
        self._fallback_events: list[dict[str, Any]] = []

        # Default fallback values for common actions
        self._default_values = {
            "email_tool": json.dumps({"success": False, "error": "Email service unavailable"}),
            "report_generator": json.dumps({"success": False, "error": "Report generation failed"}),
            "data_processor": json.dumps({"success": False, "error": "Data processing failed"}),
            "notification": json.dumps(
                {"success": False, "error": "Notification service unavailable"}
            ),
        }

    def get_fallback_config(self, action_name: str) -> dict[str, Any]:
        """
        Get fallback configuration for an action.

        Args:
            action_name: Name of the action

        Returns:
            Fallback configuration dictionary
        """
        # Check for specific action config
        for key, config in self.fallbacks.items():
            if key.lower() in action_name.lower():
                return config

        # Return default config
        return {
            "strategy": self.default_strategy,
            "default_value": self._default_values.get(
                action_name, json.dumps({"success": False, "error": "Action failed"})
            ),
        }

    async def handle_failure(
        self,
        error: Exception,
        action_name: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Handle a failure using fallback mechanisms.

        Args:
            error: The exception that occurred
            action_name: Name of the failed action
            context: Additional context about the failure

        Returns:
            Fallback result or None if no fallback available
        """
        if not self.enabled:
            return None

        action = action_name or "unknown"
        config = self.get_fallback_config(action)
        strategy = FallbackStrategy(config.get("strategy", self.default_strategy))

        # Log the fallback event
        event = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "error": str(error),
            "strategy": strategy.value,
            "context": context or {},
        }
        self._fallback_events.append(event)

        if strategy == FallbackStrategy.DEFAULT_VALUE:
            return self._apply_default_value(action, config)
        elif strategy == FallbackStrategy.SIMPLIFIED:
            return await self._apply_simplified(action, config, context)
        elif strategy == FallbackStrategy.SKIP:
            return self._apply_skip(action)
        elif strategy == FallbackStrategy.ABORT:
            return self._apply_abort(action, error)
        elif strategy == FallbackStrategy.RETRY_LATER:
            return await self._apply_retry_later(action, config, context)
        else:
            return None

    def _apply_default_value(self, action: str, config: dict[str, Any]) -> Any:
        """Apply default value fallback."""
        default = config.get("default_value")
        if default is None:
            default = self._default_values.get(
                action, json.dumps({"success": False, "fallback": True})
            )
        return default

    async def _apply_simplified(
        self, action: str, config: dict[str, Any], context: Optional[dict[str, Any]]
    ) -> Any:
        """Apply simplified version fallback."""
        simplified_result = {
            "success": True,
            "fallback": True,
            "simplified": True,
            "message": f"Used simplified version for {action}",
            "data": context.get("partial_result") if context else None,
        }
        return json.dumps(simplified_result)

    def _apply_skip(self, action: str) -> Any:
        """Apply skip fallback."""
        return json.dumps(
            {
                "success": True,
                "skipped": True,
                "message": f"Skipped {action} due to failure",
            }
        )

    def _apply_abort(self, action: str, error: Exception) -> Any:
        """Apply abort fallback."""
        return json.dumps(
            {
                "success": False,
                "aborted": True,
                "error": str(error),
                "message": f"Workflow aborted due to failure in {action}",
            }
        )

    async def _apply_retry_later(
        self, action: str, config: dict[str, Any], context: Optional[dict[str, Any]]
    ) -> Any:
        """Apply retry later fallback."""
        retry_config = {
            "action": action,
            "context": context,
            "scheduled_for": datetime.now().isoformat(),
            "max_attempts": config.get("max_retry_attempts", 3),
        }
        return json.dumps(
            {
                "success": True,
                "queued": True,
                "retry_config": retry_config,
                "message": f"{action} queued for later retry",
            }
        )

    def register_fallback(
        self,
        action_pattern: str,
        strategy: FallbackStrategy,
        **kwargs,
    ) -> None:
        """
        Register a fallback for a specific action pattern.

        Args:
            action_pattern: Pattern to match action names
            strategy: Fallback strategy to use
            **kwargs: Additional configuration for the fallback
        """
        self.fallbacks[action_pattern] = {
            "strategy": strategy.value,
            **kwargs,
        }

    def set_default_value(self, action: str, value: Any) -> None:
        """
        Set a default fallback value for an action.

        Args:
            action: Action name
            value: Default value to return on failure
        """
        self._default_values[action] = value

    def get_fallback_history(self) -> list[dict[str, Any]]:
        """Get history of fallback events."""
        return self._fallback_events.copy()

    def clear_history(self) -> None:
        """Clear fallback event history."""
        self._fallback_events.clear()

    def get_statistics(self) -> dict[str, Any]:
        """Get fallback statistics."""
        if not self._fallback_events:
            return {"total_fallbacks": 0}

        strategies: dict[str, int] = {}
        for event in self._fallback_events:
            strategy = event["strategy"]
            strategies[strategy] = strategies.get(strategy, 0) + 1

        return {
            "total_fallbacks": len(self._fallback_events),
            "by_strategy": strategies,
        }


class FallbackChain:
    """
    Chain of fallback handlers for complex failure scenarios.

    This allows trying multiple fallback strategies in sequence
    until one succeeds.
    """

    def __init__(self, strategies: Optional[list[FallbackStrategy]] = None):
        """
        Initialize the fallback chain.

        Args:
            strategies: Ordered list of strategies to try
        """
        self.strategies = strategies or [
            FallbackStrategy.SIMPLIFIED,
            FallbackStrategy.DEFAULT_VALUE,
            FallbackStrategy.SKIP,
        ]

    async def execute(
        self,
        error: Exception,
        action_name: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Execute the fallback chain.

        Args:
            error: The exception that occurred
            action_name: Name of the failed action
            context: Additional context

        Returns:
            Result from the first successful fallback
        """
        middleware = FallbackMiddleware()

        for strategy in self.strategies:
            middleware.default_strategy = strategy
            result = await middleware.handle_failure(error, action_name, context)

            if result is not None:
                return result

        return None
