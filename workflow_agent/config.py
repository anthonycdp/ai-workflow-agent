"""
Configuration management for the workflow agent.
"""

import os
from dataclasses import dataclass, field
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class AgentConfig:
    """Configuration for the workflow agent."""

    # LLM Settings
    llm_provider: LLMProvider = LLMProvider.ANTHROPIC
    model_name: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 4096

    # Retry Settings
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0

    # Human-in-the-Loop Settings
    auto_approve_safe_actions: bool = True
    require_approval_for_sensitive: bool = True
    sensitive_actions: list[str] = field(
        default_factory=lambda: [
            "send_email",
            "delete_data",
            "modify_settings",
            "external_api_call",
        ]
    )

    # Workflow Settings
    max_concurrent_tasks: int = 5
    task_timeout: float = 300.0  # 5 minutes
    enable_fallback: bool = True

    # Logging
    log_level: str = "INFO"
    enable_tracing: bool = True

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create configuration from environment variables."""
        provider_str = os.getenv("LLM_PROVIDER", "anthropic").lower()
        provider = LLMProvider.ANTHROPIC if provider_str == "anthropic" else LLMProvider.OPENAI

        return cls(
            llm_provider=provider,
            model_name=os.getenv("MODEL_NAME", "claude-sonnet-4-20250514"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
            retry_backoff=float(os.getenv("RETRY_BACKOFF", "2.0")),
            auto_approve_safe_actions=os.getenv("AUTO_APPROVE_SAFE", "true").lower() == "true",
            require_approval_for_sensitive=os.getenv("REQUIRE_APPROVAL", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_tracing=os.getenv("ENABLE_TRACING", "true").lower() == "true",
        )


@dataclass
class ToolConfig:
    """Configuration for individual tools."""

    # Email Tool
    smtp_server: str = "smtp.example.com"
    smtp_port: int = 587
    email_from: str = "agent@example.com"

    # Report Tool
    reports_dir: str = "./reports"
    templates_dir: str = "./templates"

    # Data Processing
    data_dir: str = "./data"
    output_dir: str = "./output"
    batch_size: int = 100

    @classmethod
    def from_env(cls) -> "ToolConfig":
        """Create tool configuration from environment variables."""
        return cls(
            smtp_server=os.getenv("SMTP_SERVER", "smtp.example.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            email_from=os.getenv("EMAIL_FROM", "agent@example.com"),
            reports_dir=os.getenv("REPORTS_DIR", "./reports"),
            templates_dir=os.getenv("TEMPLATES_DIR", "./templates"),
            data_dir=os.getenv("DATA_DIR", "./data"),
            output_dir=os.getenv("OUTPUT_DIR", "./output"),
            batch_size=int(os.getenv("BATCH_SIZE", "100")),
        )


# Default configurations
DEFAULT_AGENT_CONFIG = AgentConfig()
DEFAULT_TOOL_CONFIG = ToolConfig()
