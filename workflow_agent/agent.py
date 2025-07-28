"""
Core Workflow Agent implementation using LangChain.

This agent automates workflows with:
- ReAct reasoning pattern
- Tool use capabilities
- Human-in-the-loop supervision
- Fallback mechanisms
"""

import uuid
from datetime import datetime
from typing import Any, Callable, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from workflow_agent.config import AgentConfig, LLMProvider
from workflow_agent.models import (
    ApprovalDecision,
    ApprovalRequest,
    ToolResult,
    WorkflowResult,
    WorkflowStatus,
)
from workflow_agent.middleware import (
    HumanApprovalMiddleware,
    RetryMiddleware,
    FallbackMiddleware,
)


class WorkflowAgent:
    """
    AI Agent for Workflow Automation.

    This agent uses the ReAct (Reasoning + Acting) pattern to:
    1. Analyze incoming tasks
    2. Plan actions using available tools
    3. Execute actions with human oversight
    4. Handle failures with fallback mechanisms
    5. Report results and learn from feedback

    Attributes:
        config: Agent configuration
        tools: Dictionary of available tools
        middleware: List of middleware for processing
        llm: Language model for reasoning
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        tools: Optional[list[BaseTool]] = None,
    ):
        """
        Initialize the workflow agent.

        Args:
            config: Agent configuration (uses defaults if not provided)
            tools: List of tools available to the agent
        """
        self.config = config or AgentConfig()
        self.tools: dict[str, BaseTool] = {}
        self._tool_list: list[BaseTool] = []
        self.llm: Any = None

        # Initialize LLM
        self._init_llm()

        # Initialize middleware stack
        self._init_middleware()

        # Register provided tools
        if tools:
            for tool in tools:
                self.register_tool(tool)

        # State management
        self._workflow_history: list[WorkflowResult] = []
        self._approval_queue: list[ApprovalRequest] = []

    def _init_llm(self) -> None:
        """Initialize the language model based on configuration."""
        if self.config.llm_provider == LLMProvider.ANTHROPIC:
            self.llm = ChatAnthropic(
                model_name=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens_to_sample=self.config.max_tokens,
                timeout=None,
                max_retries=self.config.max_retries,
                stop=None,
            )
        else:
            self.llm = ChatOpenAI(
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_completion_tokens=self.config.max_tokens,
                max_retries=self.config.max_retries,
            )

        # Bind tools to LLM
        if self._tool_list:
            self.llm = self.llm.bind_tools(self._tool_list)

    def _init_middleware(self) -> None:
        """Initialize middleware stack."""
        self.retry_middleware = RetryMiddleware(
            max_retries=self.config.max_retries,
            delay=self.config.retry_delay,
            backoff=self.config.retry_backoff,
        )

        self.approval_middleware = HumanApprovalMiddleware(
            auto_approve_safe=self.config.auto_approve_safe_actions,
            sensitive_actions=self.config.sensitive_actions,
        )

        self.fallback_middleware = FallbackMiddleware(enabled=self.config.enable_fallback)

        self._middleware = [
            self.retry_middleware,
            self.approval_middleware,
            self.fallback_middleware,
        ]

    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool with the agent.

        Args:
            tool: The tool to register
        """
        self.tools[tool.name] = tool
        self._tool_list.append(tool)
        # Re-bind tools to LLM
        self.llm = self.llm.bind_tools(self._tool_list)

    def register_function_tool(
        self,
        func: Callable,
        name: str,
        description: str,
    ) -> None:
        """
        Register a function as a tool.

        Args:
            func: The function to wrap as a tool
            name: Tool name
            description: Tool description
        """
        from langchain_core.tools import StructuredTool

        tool = StructuredTool.from_function(
            func=func,
            name=name,
            description=description,
        )
        self.register_tool(tool)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """You are an AI Workflow Agent designed to automate business workflows efficiently and safely.

Your capabilities include:
- Email triage and response drafting
- Report generation and data analysis
- Data processing and transformation
- Task coordination and scheduling

Guidelines for your behavior:
1. Always explain your reasoning before taking action
2. For sensitive operations, wait for human approval
3. If a tool fails, try alternative approaches
4. Be transparent about uncertainties and limitations
5. Provide clear summaries of completed actions

When you need to use a tool:
1. First explain what you plan to do and why
2. Call the appropriate tool with correct parameters
3. Process the result and determine next steps
4. Report outcomes clearly to the user

Available tools:
{tool_descriptions}

Remember: Your goal is to be helpful, safe, and efficient. When in doubt, ask for clarification or approval."""

    def _format_tool_descriptions(self) -> str:
        """Format tool descriptions for the system prompt."""
        descriptions = []
        for name, tool in self.tools.items():
            desc = f"- {name}: {tool.description}"
            descriptions.append(desc)
        return "\n".join(descriptions)

    async def process(self, task: str, context: Optional[dict[str, Any]] = None) -> WorkflowResult:
        """
        Process a task using the agent's workflow.

        This is the main entry point for running workflows. The agent will:
        1. Analyze the task
        2. Plan and execute actions
        3. Handle approvals if needed
        4. Return results

        Args:
            task: The task description or request
            context: Additional context for the task

        Returns:
            WorkflowResult with execution details
        """
        workflow_id = str(uuid.uuid4())
        result = WorkflowResult(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
        )

        try:
            messages = self._build_messages(task, context)
            while True:
                response = await self.llm.ainvoke(messages)

                if not getattr(response, "tool_calls", None):
                    self._complete_workflow(result, response.content)
                    break

                paused_for_approval = await self._handle_tool_calls(response, messages, result)
                if paused_for_approval:
                    break

                result.steps_total += 1

                if result.steps_completed > 50:
                    result.errors.append("Maximum steps exceeded")
                    result.status = WorkflowStatus.FAILED
                    break

        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.errors.append(str(e))

            # Try fallback if enabled
            if self.config.enable_fallback:
                fallback_result = await self.fallback_middleware.handle_failure(e, task)
                if fallback_result:
                    result.output["fallback"] = fallback_result

        result.completed_at = datetime.now()
        self._workflow_history.append(result)
        return result

    def _complete_workflow(self, result: WorkflowResult, response_content: Any) -> None:
        """Store the final response and mark the workflow as complete."""
        result.output["response"] = response_content
        result.status = WorkflowStatus.COMPLETED

    async def _handle_tool_calls(
        self,
        response: Any,
        messages: list[BaseMessage],
        result: WorkflowResult,
    ) -> bool:
        """Execute tool calls from a model response."""
        messages.append(response)

        for tool_call in response.tool_calls:
            tool_call_id = str(tool_call.get("id") or uuid.uuid4())
            tool_result = await self._execute_tool_with_middleware(
                tool_call["name"],
                tool_call["args"],
                tool_call_id,
            )

            tool_result, paused_for_approval = await self._resolve_approval(tool_result, result)
            if paused_for_approval:
                return True

            messages.append(
                ToolMessage(
                    content=str(tool_result.output),
                    tool_call_id=tool_call_id,
                )
            )

            result.steps_completed += 1
            if not tool_result.success:
                result.errors.append(f"Tool {tool_call['name']} failed: {tool_result.error}")

        return False

    async def _resolve_approval(
        self,
        tool_result: ToolResult,
        result: WorkflowResult,
    ) -> tuple[ToolResult, bool]:
        """Resolve approval requirements for a tool result."""
        if not tool_result.requires_approval:
            return tool_result, False

        result.status = WorkflowStatus.WAITING_APPROVAL
        result.approvals_requested += 1

        if not self.config.auto_approve_safe_actions:
            result.output["pending_approval"] = tool_result.approval_request or {}
            return tool_result, True

        approved_result = await self._execute_approved_action(tool_result)
        result.approvals_granted += 1
        return approved_result, False

    def _build_messages(
        self, task: str, context: Optional[dict[str, Any]] = None
    ) -> list[BaseMessage]:
        """Build message list for the LLM."""
        system_prompt = self._get_system_prompt().format(
            tool_descriptions=self._format_tool_descriptions()
        )

        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]

        # Add context if provided
        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            messages.append(HumanMessage(content=f"Context:\n{context_str}\n\nTask: {task}"))
        else:
            messages.append(HumanMessage(content=task))

        return messages

    async def _execute_tool_with_middleware(
        self, tool_name: str, args: dict[str, Any], call_id: str
    ) -> ToolResult:
        """Execute a tool through the middleware stack."""
        tool = self.tools.get(tool_name)

        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool '{tool_name}' not found",
            )

        try:
            requires_approval = self.approval_middleware.requires_approval(tool_name, args)
            if requires_approval:
                approval_request = await self.approval_middleware.create_approval_request(
                    tool_name,
                    args,
                    {"call_id": call_id},
                )
                self._approval_queue.append(approval_request)
                return ToolResult(
                    success=True,
                    output="Pending approval",
                    requires_approval=True,
                    approval_request={
                        "request_id": approval_request.request_id,
                        "tool_name": tool_name,
                        "args": args,
                        "call_id": call_id,
                    },
                )

            result = await self.retry_middleware.execute(lambda: tool.ainvoke(args))
            return ToolResult(
                success=True,
                output=result,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )

    def _remove_pending_approval(self, request_id: str) -> None:
        """Remove an approval request from all in-memory queues."""
        self._approval_queue = [
            request for request in self._approval_queue if request.request_id != request_id
        ]
        self.approval_middleware.clear_request(request_id)

    async def _execute_approved_action(self, pending_result: ToolResult) -> ToolResult:
        """Execute a previously approved action."""
        approval_data = pending_result.approval_request
        if not approval_data:
            return pending_result

        tool_name = str(approval_data.get("tool_name", ""))
        args = approval_data.get("args")
        request_id = approval_data.get("request_id")
        if not tool_name or not isinstance(args, dict):
            return ToolResult(success=False, output=None, error="Invalid approval request data")

        tool = self.tools.get(tool_name)

        if tool:
            try:
                result = await tool.ainvoke(args)
                if isinstance(request_id, str):
                    self._remove_pending_approval(request_id)
                return ToolResult(success=True, output=result)
            except Exception as e:
                return ToolResult(success=False, output=None, error=str(e))

        return pending_result

    async def approve_action(
        self, request_id: str, decision: ApprovalDecision, modified_input: Optional[dict] = None
    ) -> ToolResult:
        """
        Approve or reject a pending action.

        Args:
            request_id: ID of the approval request
            decision: The approval decision
            modified_input: Optional modified input if editing

        Returns:
            ToolResult from executing the approved action
        """
        # Find the pending request
        for request in self._approval_queue:
            if request.request_id == request_id:
                request.decision = decision
                request.modified_input = modified_input
                request_args = modified_input or request.modified_input or request.proposed_input

                if decision != ApprovalDecision.APPROVE:
                    self._remove_pending_approval(request.request_id)
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Action rejected: {decision.value}",
                    )

                return await self._execute_approved_action(
                    ToolResult(
                        success=True,
                        output="Pending",
                        requires_approval=True,
                        approval_request={
                            "request_id": request.request_id,
                            "tool_name": request.tool_name,
                            "args": request_args,
                        },
                    )
                )

        return ToolResult(
            success=False,
            output=None,
            error=f"Request {request_id} not found",
        )

    def get_workflow_history(self) -> list[WorkflowResult]:
        """Get history of workflow executions."""
        return self._workflow_history.copy()

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        """Get list of actions pending approval."""
        return self._approval_queue.copy()
