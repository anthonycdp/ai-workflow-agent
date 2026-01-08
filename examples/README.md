# AI Workflow Agent - Examples

This directory contains example scripts demonstrating how to use the AI Workflow Agent.

## Examples

### 1. Basic Usage (`basic_usage.py`)

Demonstrates:
- Creating and configuring the agent
- Registering tools
- Using tools directly for email triage
- Generating reports
- Processing data
- Sending notifications

```bash
python examples/basic_usage.py
```

### 2. Workflow Orchestration (`workflow_example.py`)

Demonstrates:
- Setting up the workflow orchestrator
- Using predefined workflow templates
- Creating custom workflows
- Variable substitution
- Workflow step configuration

```bash
python examples/workflow_example.py
```

### 3. Human-in-the-Loop (`human_in_loop_example.py`)

Demonstrates:
- Custom approval handlers
- Risk level assessment
- Sensitive action detection
- Retry middleware with backoff
- Fallback mechanisms

```bash
python examples/human_in_loop_example.py
```

## Running the Examples

1. Ensure you have installed the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. Run an example:
   ```bash
   python examples/basic_usage.py
   ```

## Note on LLM Calls

These examples can run in "simulation mode" without actual LLM API calls by using the tools directly. For full agent functionality with reasoning, you'll need to configure API keys for either:
- Anthropic (default): Set `ANTHROPIC_API_KEY`
- OpenAI: Set `OPENAI_API_KEY` and change `LLM_PROVIDER=openai`
