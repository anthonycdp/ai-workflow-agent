# AI Workflow Agent

> An intelligent agent framework for workflow automation with human-in-the-loop supervision, fallback mechanisms, and tool use capabilities.

## Overview

This project demonstrates how to build production-ready AI agents using LangChain that can automate complex workflows while maintaining human oversight. The agent uses the ReAct (Reasoning + Acting) pattern to analyze tasks, plan actions, and execute them safely with appropriate safeguards.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI WORKFLOW AGENT                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐        │
│    │  User    │───▶│  Agent   │───▶│Middleware│───▶│  Tools   │        │
│    │ Request  │    │  Core    │    │  Stack   │    │          │        │
│    └──────────┘    └──────────┘    └──────────┘    └──────────┘        │
│         │               │               │               │               │
│         │               │               │               │               │
│         │               ▼               ▼               ▼               │
│         │        ┌──────────────────────────────────────────┐          │
│         │        │              SAFETY LAYER                 │          │
│         │        │  • Human Approval for Sensitive Actions  │          │
│         │        │  • Automatic Retry with Backoff          │          │
│         │        │  • Graceful Fallback Mechanisms          │          │
│         │        └──────────────────────────────────────────┘          │
│         │                                                                │
│         └──────────────▶ Results with Audit Trail                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features

### Core Capabilities
- **ReAct Reasoning**: Agent reasons about tasks before acting
- **Tool Use**: Extensible tool system for various operations
- **Workflow Templates**: Pre-built workflows for common use cases
- **State Management**: Track execution progress and in-memory history

### Safety Features
- **Human-in-the-Loop**: Require approval for sensitive actions
- **Retry with Backoff**: Automatic retry for transient failures
- **Fallback Mechanisms**: Graceful degradation when tools fail
- **Risk Assessment**: Automatic evaluation of action risk levels

### Available Tools
| Tool | Description | Sensitive Actions |
|------|-------------|-------------------|
| Email | Triage, draft, send emails | `send` |
| Report Generator | Create formatted reports | `schedule` |
| Data Processor | ETL and data transformation | None |
| Notification | Send alerts and messages | `sms`, `webhook`, `schedule` |

## Architecture

### System Architecture

```
                                    ┌─────────────────┐
                                    │ CLI / Python API│
                                    │   Interface     │
                                    └────────┬────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        WORKFLOW ORCHESTRATOR                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Workflow   │  │  Workflow   │  │  Workflow   │  │   Custom    │   │
│  │  Templates  │  │   Engine    │  │   State     │  │   Builder   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          WORKFLOW AGENT                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  ReAct      │  │    LLM      │  │   Tool      │  │   Action    │   │
│  │  Reasoning  │  │  Interface  │  │  Registry   │  │   Logger    │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          MIDDLEWARE STACK                               │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  1. Retry Middleware → 2. Human Approval → 3. Fallback         │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                             TOOLS                                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │   Email    │  │  Report    │  │    Data    │  │Notification│       │
│  │   Tool     │  │ Generator  │  │ Processor  │  │    Tool    │       │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘       │
└────────────────────────────────────────────────────────────────────────┘
```

### ReAct Agent Loop

The agent follows the ReAct (Reasoning + Acting) pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│                    REACT AGENT LOOP                              │
│                                                                  │
│    ┌─────────┐                                                  │
│    │  START  │                                                  │
│    └────┬────┘                                                  │
│         │                                                        │
│         ▼                                                        │
│    ┌─────────────────────────────────────┐                      │
│    │           REASON                     │                      │
│    │  "What should I do next?"            │                      │
│    │  Analyze current state and goal      │                      │
│    └────────────────┬────────────────────┘                      │
│                     │                                            │
│                     ▼                                            │
│    ┌─────────────────────────────────────┐                      │
│    │           DECIDE                     │                      │
│    │  "Which tool should I use?"          │                      │
│    │  Select action and parameters        │                      │
│    └────────────────┬────────────────────┘                      │
│                     │                                            │
│                     ▼                                            │
│              ┌──────┴──────┐                                    │
│              │             │                                    │
│         ┌────┴────┐   ┌────┴────┐                              │
│         │ SAFE    │   │SENSITIVE│                              │
│         │ ACTION  │   │ ACTION  │                              │
│         └────┬────┘   └────┬────┘                              │
│              │             │                                    │
│              │        ┌────┴────┐                              │
│              │        │  AWAIT  │                              │
│              │        │APPROVAL │                              │
│              │        └────┬────┘                              │
│              │             │                                    │
│              └──────┬──────┘                                    │
│                     │                                            │
│                     ▼                                            │
│    ┌─────────────────────────────────────┐                      │
│    │           ACT                        │                      │
│    │  Execute tool with parameters        │                      │
│    │  Apply retry/fallback middleware     │                      │
│    └────────────────┬────────────────────┘                      │
│                     │                                            │
│                     ▼                                            │
│    ┌─────────────────────────────────────┐                      │
│    │           OBSERVE                    │                      │
│    │  Process tool result                 │                      │
│    │  Update state                        │                      │
│    └────────────────┬────────────────────┘                      │
│                     │                                            │
│                     ▼                                            │
│              ┌──────┴──────┐                                    │
│              │             │                                    │
│         ┌────┴────┐   ┌────┴────┐                              │
│         │ DONE    │   │CONTINUE │                              │
│         └────┬────┘   └────┬────┘                              │
│              │             │                                    │
│              ▼             │                                    │
│    ┌─────────────────┐     │                                    │
│    │     OUTPUT      │     │                                    │
│    └─────────────────┘     │                                    │
│                            │                                    │
│                            └────────────┐                       │
│                                         │                       │
│                          ┌──────────────┘                       │
│                          │                                      │
│                          ▼                                      │
│                   (Back to REASON)                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Human-in-the-Loop Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                  HUMAN-IN-THE-LOOP FLOW                             │
│                                                                     │
│    Agent Request                                                    │
│         │                                                           │
│         ▼                                                           │
│    ┌────────────────┐                                               │
│    │ Action Attempt │                                               │
│    └───────┬────────┘                                               │
│            │                                                         │
│            ▼                                                         │
│    ┌────────────────────────────────────┐                          │
│    │        MIDDLEWARE CHECK             │                          │
│    │  Is this action sensitive?          │                          │
│    └───────────────┬────────────────────┘                          │
│                    │                                                │
│           ┌────────┴────────┐                                      │
│           │                 │                                      │
│        ┌──┴──┐          ┌───┴───┐                                 │
│        │ NO  │          │  YES  │                                 │
│        └──┬──┘          └───┬───┘                                 │
│           │                 │                                      │
│           ▼                 ▼                                      │
│    ┌──────────────┐  ┌──────────────────┐                        │
│    │   Execute    │  │  Create Approval │                        │
│    │   Directly   │  │     Request      │                        │
│    └──────────────┘  └────────┬─────────┘                        │
│                              │                                    │
│                              ▼                                    │
│                    ┌─────────────────┐                            │
│                    │  WAIT FOR       │                            │
│                    │  HUMAN INPUT    │                            │
│                    └────────┬────────┘                            │
│                             │                                     │
│           ┌─────────────────┼─────────────────┐                  │
│           │                 │                 │                  │
│      ┌────┴────┐      ┌─────┴─────┐     ┌────┴────┐            │
│      │ APPROVE │      │   REJECT  │     │  EDIT   │            │
│      └────┬────┘      └─────┬─────┘     └────┬────┘            │
│           │                 │                 │                  │
│           ▼                 ▼                 ▼                  │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│    │   Execute    │  │   Return     │  │  Execute     │        │
│    │   Original   │  │   Error      │  │  Modified    │        │
│    └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Error Handling Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                   ERROR HANDLING FLOW                               │
│                                                                     │
│    Tool Execution                                                   │
│         │                                                           │
│         ▼                                                           │
│    ┌────────────────┐                                               │
│    │    SUCCESS?    │                                               │
│    └───────┬────────┘                                               │
│            │                                                         │
│     ┌──────┴──────┐                                                │
│     │             │                                                │
│  ┌──┴──┐      ┌───┴───┐                                           │
│  │ YES │      │  NO   │                                           │
│  └──┬──┘      └───┬───┘                                           │
│     │             │                                                 │
│     ▼             ▼                                                 │
│  Return       ┌────────────────────────────────┐                  │
│  Result       │      RETRY MIDDLEWARE           │                  │
│               │  Retry count < max_retries?     │                  │
│               └─────────────┬──────────────────┘                  │
│                             │                                      │
│                    ┌────────┴────────┐                            │
│                    │                 │                            │
│                 ┌──┴──┐          ┌───┴───┐                       │
│                 │ YES │          │  NO   │                       │
│                 └──┬──┘          └───┬───┘                       │
│                    │                 │                            │
│                    ▼                 ▼                            │
│            ┌──────────────┐  ┌──────────────────┐               │
│            │ Wait with    │  │ FALLBACK         │               │
│            │ exponential  │  │ MIDDLEWARE       │               │
│            │ backoff      │  │                  │               │
│            └──────┬───────┘  └────────┬─────────┘               │
│                   │                   │                          │
│                   │          ┌───────┴────────┐                 │
│                   │          │                │                 │
│                   │    ┌─────┴─────┐    ┌─────┴─────┐          │
│                   │    │  DEFAULT  │    │  SIMPLIFY │          │
│                   │    │  VALUE    │    │  OR SKIP  │          │
│                   │    └─────┬─────┘    └─────┬─────┘          │
│                   │          │                │                 │
│                   │          └───────┬────────┘                 │
│                   │                  │                          │
│                   ▼                  ▼                          │
│            Retry Execution    Return Fallback                   │
│                   │           Result                             │
│                   │                                               │
│                   └──────────┐                                   │
│                              │                                    │
│                              ▼                                    │
│                      (Back to Start)                              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
ai-workflow-agent/
├── workflow_agent/
│   ├── __init__.py           # Package exports
│   ├── agent.py              # Core WorkflowAgent implementation
│   ├── config.py             # Configuration management
│   ├── models.py             # Pydantic data models
│   ├── cli.py                # Command-line interface
│   ├── utils.py              # Utility functions
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── email.py          # Email triage and management
│   │   ├── report.py         # Report generation
│   │   ├── data.py           # Data processing
│   │   └── notification.py   # Notifications
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── human_approval.py # Human-in-the-loop
│   │   ├── retry.py          # Retry with backoff
│   │   └── fallback.py       # Fallback mechanisms
│   │
│   └── workflows/
│       ├── __init__.py
│       ├── orchestrator.py   # Workflow orchestration
│       └── templates.py      # Pre-built workflows
│
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_cli.py
│   ├── test_tools.py
│   ├── test_middleware.py
│   └── test_orchestrator.py
│
├── docs/
│   └── ...
│
├── examples/
│   ├── basic_usage.py
│   ├── workflow_example.py
│   └── human_in_loop_example.py
│
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

## Installation

### Prerequisites
- Python 3.10 or higher
- An Anthropic or OpenAI API key for commands that initialize the agent

### Setup

```bash
# Clone or navigate to the project
cd ai-workflow-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package so the `workflow-agent` command is available
python -m pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env  # On Windows PowerShell: Copy-Item .env.example .env
# Edit .env and add your API keys
```

### Configuration

```bash
# .env file
LLM_PROVIDER=anthropic
MODEL_NAME=claude-sonnet-4-20250514
TEMPERATURE=0.7
MAX_TOKENS=4096

# Safety settings
AUTO_APPROVE_SAFE=true
REQUIRE_APPROVAL=true
ENABLE_TRACING=true
```

## Usage

### Command Line Interface

```bash
# List available workflows
workflow-agent list

# Run a workflow
workflow-agent run email_triage

# Interactive chat mode
workflow-agent chat

# View execution history for the current in-memory process state
workflow-agent history

# List available tools
workflow-agent tools

# Show configuration
workflow-agent config

# Approve pending actions for the current in-memory process state
workflow-agent approve
```

Notes:
- `workflow-agent list`, `tools`, and `config` do not require model credentials.
- `workflow-agent run` and `chat` initialize an LLM-backed agent and require provider credentials.
- `history` and `approve` currently use in-memory state only. They do not persist data across separate CLI invocations.

### Python API

```python
import asyncio
from workflow_agent.agent import WorkflowAgent
from workflow_agent.config import AgentConfig
from workflow_agent.tools import EmailTool, ReportGeneratorTool

async def main():
    # Create agent with configuration
    config = AgentConfig(
        model_name="claude-sonnet-4-20250514",
        auto_approve_safe_actions=True,
    )
    agent = WorkflowAgent(config=config)

    # Register tools
    agent.register_tool(EmailTool())
    agent.register_tool(ReportGeneratorTool())

    # Process a task
    result = await agent.process(
        "Triage the following emails and generate a summary report",
        context={"emails": [...]}
    )

    print(f"Status: {result.status}")
    print(f"Output: {result.output}")

asyncio.run(main())
```

### Using Workflows

```python
from workflow_agent.workflows import WorkflowOrchestrator
from workflow_agent.workflows.templates import EmailTriageWorkflow

async def main():
    orchestrator = WorkflowOrchestrator()
    orchestrator.register_workflow(EmailTriageWorkflow())

    # Execute with variables
    result = await orchestrator.execute(
        "email_triage",
        variables={"batch_size": 100}
    )

asyncio.run(main())
```

### Custom Approval Handler

```python
from workflow_agent.middleware.human_approval import ApprovalHandler, ApprovalDecision
from workflow_agent.models import ApprovalRequest

class SlackApprovalHandler(ApprovalHandler):
    """Send approval requests to Slack."""

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        # Send to Slack and wait for response
        message = self._format_request(request)
        await self._send_to_slack(message)

        # Wait for response (polling or webhook)
        response = await self._wait_for_response(request.request_id)

        return ApprovalDecision(response)

# Use custom handler
from workflow_agent.middleware import HumanApprovalMiddleware

middleware = HumanApprovalMiddleware(
    approval_handler=SlackApprovalHandler()
)
```

## Workflow Templates

### Email Triage Workflow
Automatically categorizes, prioritizes, and drafts responses for emails.

```python
# Steps:
# 1. Categorize emails (work, personal, promotional, etc.)
# 2. Prioritize by urgency and importance
# 3. Draft responses for action-required emails
# 4. Send notifications for urgent items (requires approval)
```

### Report Generation Workflow
Collects, processes, and distributes automated reports.

```python
# Steps:
# 1. Fetch data from specified sources
# 2. Process and analyze the data
# 3. Generate formatted report
# 4. Distribute to recipients (requires approval)
```

### Data Pipeline Workflow
ETL pipeline for data processing and transformation.

```python
# Steps:
# 1. Ingest raw data from source
# 2. Validate data quality
# 3. Transform and enrich data
# 4. Export to destination
# 5. Send completion notification
```

## Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=workflow_agent

# Run specific test file
python -m pytest tests/test_tools.py -v

# Run with markers
python -m pytest -m asyncio

# Run static checks
ruff check .
black --check .
python -m mypy workflow_agent
```

## Key Design Decisions

### 1. ReAct Pattern
The agent uses Reasoning + Acting to break down complex tasks into steps, reasoning about each action before execution.

### 2. Middleware Architecture
Middleware provides a clean separation of concerns:
- **Retry**: Handles transient failures
- **Human Approval**: Ensures safety for sensitive actions
- **Fallback**: Provides graceful degradation

### 3. Tool Abstraction
Tools follow a consistent interface, making it easy to add new capabilities without modifying the core agent.

### 4. Workflow Templates
Pre-built templates demonstrate best practices and provide starting points for common use cases.

### 5. State Management
Execution state is tracked in memory during runtime. The current CLI does not persist workflow history or approval queues across separate process executions.

## Production Considerations

### Security
- All sensitive actions require approval by default
- API keys are loaded from environment variables
- Input validation on all tool parameters

### Scalability
- Async/await throughout for concurrent operations
- Batch processing support in data tools
- Configurable concurrency limits

### Observability
- Structured logging with configurable levels
- In-memory execution history and middleware statistics
- Middleware statistics tracking

### Reliability
- Automatic retry with exponential backoff
- Graceful fallback mechanisms
- Comprehensive error handling

## License

MIT License - See LICENSE file for details.

## Acknowledgments

Built with:
- [LangChain](https://github.com/langchain-ai/langchain) - Agent framework
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [Typer](https://github.com/tiangolo/typer) - CLI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
