# Agent Frameworks Research: Local LLM Agent for Azure AI Foundry + Teams

**Research date:** 2026-05-13  
**Status:** Complete  
**Goal:** Build a locally-running Python LLM agent that calls an Azure AI Foundry-hosted model and reads/writes Microsoft Teams messages via Microsoft Graph API.

---

## Table of Contents

1. [Research Questions](#research-questions)
2. [Framework Comparison Table](#framework-comparison-table)
3. [Framework Deep Dives](#framework-deep-dives)
   - [LangChain](#1-langchain-python)
   - [Semantic Kernel / Microsoft Agent Framework](#2-semantic-kernel--microsoft-agent-framework)
   - [AutoGen](#3-autogen-microsoft)
   - [Azure AI Agents Service (Foundry Agent Service)](#4-azure-ai-agents-service--foundry-agent-service)
   - [Custom Agent Loop](#5-custom-agent-loop-no-framework)
4. [Microsoft Graph / Teams Tool Patterns](#microsoft-graph--teams-tool-patterns)
5. [Final Recommendation](#final-recommendation)
6. [References](#references)

---

## Research Questions

For each framework:
- How easy is Azure AI Foundry LLM integration?
- How easy is custom tool definition (for Teams API calls)?
- Local execution support (no cloud orchestration needed)?
- Learning curve and boilerplate?
- Active maintenance and 2025/2026 release status?

---

## Framework Comparison Table

| Criterion | LangChain | Semantic Kernel / MAF | AutoGen | Foundry Agent Service | Custom Loop |
|---|---|---|---|---|---|
| **Azure AI Foundry integration** | ✅ `langchain-azure-ai` 1.2.3 (Apr 2026), `AzureChatOpenAI` | ✅ `AzureChatCompletion` connector, v1 stable | ✅ `AzureOpenAIChatCompletionClient` + `AzureAIChatCompletionClient` | ✅ Native (it IS the Foundry service) | ✅ `azure-ai-inference` / `openai` SDK directly |
| **Custom tool definition** | ✅ `@tool` decorator, plain functions | ✅ `@kernel_function` decorator, class-based plugins | ✅ Plain Python async functions passed as list | ⚠️ Tools hosted in Foundry (not fully local) | ✅ Parse JSON tool calls manually |
| **Local execution** | ✅ Fully local Python process | ✅ Fully local Python process | ✅ Fully local Python process | ❌ Hosted service (cloud) | ✅ Fully local |
| **Complexity / boilerplate** | Low–medium (new `create_agent` API is simple) | Medium (Kernel + service + plugin wiring) | Low–medium (async-first, requires `asyncio`) | High setup, low agent code | Very low |
| **Learning curve** | Low (huge community, many examples) | Medium (Microsoft-specific concepts) | Medium (async paradigm, new 0.4+ API) | Medium–High (Foundry portal + SDK) | Very low |
| **Active maintenance (2025/2026)** | ✅ langchain 1.x + langchain-azure-ai 1.2.3 (Apr 2026) | ✅ SK v1 stable; rebranded as Microsoft Agent Framework 1.0 | ✅ autogen-agentchat 0.7.5 (Sep 2025) | ✅ Foundry Agent Service GA + Hosted agents (preview) | N/A (no framework to maintain) |
| **Multi-agent support** | ✅ Via LangGraph | ✅ GroupChatOrchestration, RoundRobin | ✅ Native (core design goal) | ✅ Workflow agents, A2A protocol | ❌ Manual |
| **Teams / M365 distribution** | ❌ Not built-in | ❌ Not built-in | ❌ Not built-in | ✅ Built-in publishing to Teams/M365 Copilot | ❌ Manual |
| **Best for this use case** | ✅ Strong fit | ✅ Strong fit | ✅ Good fit | ❌ Wrong abstraction level | ⚠️ Fine for trivial needs |

---

## Framework Deep Dives

---

### 1. LangChain (Python)

#### Package Setup

```bash
pip install langchain langchain-openai langchain-azure-ai
```

#### Azure AI Foundry LLM Integration

Two approaches are available:

**Option A — `langchain-azure-ai` (recommended for full Foundry support, v1.2.3, Apr 2026)**

```python
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel
from azure.identity import DefaultAzureCredential

model = AzureAIOpenAIApiChatModel(
    endpoint="https://{resource-name}.services.ai.azure.com/openai/v1",
    credential=DefaultAzureCredential(),  # or API key string
    model="gpt-4o"  # deployment name in Foundry
)
```

**Option B — `langchain-openai` with v1 API (simpler, supports all OpenAI-compatible Foundry models)**

```python
from langchain_openai import ChatOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

llm = ChatOpenAI(
    model="gpt-4o",  # Azure deployment name
    base_url="https://{resource-name}.openai.azure.com/openai/v1/",
    api_key=token_provider,  # callable handles token refresh
)
```

#### Custom Tool Definition (Teams API)

```python
import requests
from langchain.tools import tool
from langchain.agents import create_agent

@tool
def read_teams_messages(team_id: str, channel_id: str, limit: int = 10) -> str:
    """Read the most recent messages from a Microsoft Teams channel.
    
    Args:
        team_id: The Teams group/team ID.
        channel_id: The channel ID within the team.
        limit: Maximum number of messages to return.
    """
    headers = {"Authorization": f"Bearer {get_graph_token()}"}
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
    resp = requests.get(url, headers=headers, params={"$top": limit})
    resp.raise_for_status()
    messages = resp.json().get("value", [])
    return "\n".join(
        f"[{m['createdDateTime']}] {m['from']['user']['displayName']}: {m['body']['content']}"
        for m in messages
    )

@tool
def send_teams_message(team_id: str, channel_id: str, message: str) -> str:
    """Send a message to a Microsoft Teams channel.
    
    Args:
        team_id: The Teams group/team ID.
        channel_id: The channel ID within the team.
        message: The message text to send (HTML supported).
    """
    headers = {
        "Authorization": f"Bearer {get_graph_token()}",
        "Content-Type": "application/json"
    }
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
    payload = {"body": {"contentType": "html", "content": message}}
    resp = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    return f"Message sent. ID: {resp.json()['id']}"

# Build the agent — runs entirely locally
agent = create_agent(
    model=llm,
    tools=[read_teams_messages, send_teams_message],
    system_prompt="You are a Teams assistant. Help users read and write messages."
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "What are the latest 5 messages in #general?"}]
})
print(result["messages"][-1].content)
```

#### Architecture Notes (LangChain 1.x)

- `create_agent` builds a **LangGraph-backed** ReAct agent loop
- Tools can be plain Python functions or coroutines — no schema annotation required (docstrings become tool descriptions)
- `@tool` decorator lets you customize name, description, args schema
- Middleware hooks (`@wrap_tool_call`, `@before_model`, etc.) for error handling and retries
- Streaming supported via `agent.stream()`
- Full local execution — no cloud orchestration

#### Pros

- Largest community, most StackOverflow/GitHub answers
- `langchain-azure-ai` 1.2.3 (Apr 2026) provides first-class Foundry support, including `AgentServiceFactory` to run Foundry agents as LangGraph nodes
- `create_agent` is simple; hides LangGraph complexity from beginners
- Very good Azure OpenAI / Foundry documentation
- Supports non-OpenAI Foundry models (Mistral, Llama, DeepSeek) via same API
- `init_chat_model("azure_ai:gpt-4o")` works with provider string inference

#### Cons

- `langchain-azure-ai` has had breaking API changes across minor versions (v0 → v1)
- LangGraph can be complex to debug at scale
- Occasional ecosystem fragmentation (`langchain-core` vs `langchain` vs provider packages)

---

### 2. Semantic Kernel / Microsoft Agent Framework

> **Important (2026):** Semantic Kernel Python is now the foundation for **Microsoft Agent Framework (MAF) 1.0**, which is the official enterprise successor. The `semantic-kernel` PyPI package is still the install target; the new stable APIs are backward-compatible.
>
> Source: https://github.com/microsoft/semantic-kernel/tree/main/python — README updated 2 weeks ago.

#### Package Setup

```bash
pip install semantic-kernel  # Python 3.10+
```

#### Azure AI Foundry LLM Integration

```python
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

service = AzureChatCompletion(
    api_key="...",                          # or use DefaultAzureCredential
    endpoint="https://{resource}.openai.azure.com/",
    deployment_name="gpt-4o",
    api_version="2024-06-01"
)
```

For non-Azure-OpenAI Foundry models (via `azure-ai-inference`), use the `AzureAIInferenceChatCompletion` connector (available in SK Python).

#### Custom Tool Definition (Teams API)

Tools are defined as **plugins** — Python classes with methods decorated `@kernel_function`:

```python
from typing import Annotated
import requests
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatPromptExecutionSettings

class TeamsPlugin:
    def __init__(self, graph_token_provider):
        self._token_provider = graph_token_provider

    @kernel_function(description="Read recent messages from a Microsoft Teams channel")
    def read_messages(
        self,
        team_id: Annotated[str, "The Teams group/team ID"],
        channel_id: Annotated[str, "The channel ID"],
        limit: Annotated[int, "Max messages to return"] = 10
    ) -> Annotated[str, "The recent messages as formatted text"]:
        headers = {"Authorization": f"Bearer {self._token_provider()}"}
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
        resp = requests.get(url, headers=headers, params={"$top": limit})
        resp.raise_for_status()
        msgs = resp.json().get("value", [])
        return "\n".join(
            f"[{m['createdDateTime']}] {m['from']['user']['displayName']}: {m['body']['content']}"
            for m in msgs
        )

    @kernel_function(description="Send a message to a Microsoft Teams channel")
    def send_message(
        self,
        team_id: Annotated[str, "The Teams group/team ID"],
        channel_id: Annotated[str, "The channel ID"],
        message: Annotated[str, "The message text to send"]
    ) -> Annotated[str, "Confirmation with message ID"]:
        headers = {
            "Authorization": f"Bearer {self._token_provider()}",
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
        resp = requests.post(url, json={"body": {"contentType": "text", "content": message}}, headers=headers)
        resp.raise_for_status()
        return f"Sent. ID: {resp.json()['id']}"

# Create the agent
import asyncio

async def run():
    settings = OpenAIChatPromptExecutionSettings()
    settings.function_choice_behavior = "auto"

    agent = ChatCompletionAgent(
        service=AzureChatCompletion(),
        name="TeamsAgent",
        instructions="You are a Teams assistant.",
        plugins=[TeamsPlugin(get_graph_token)],
        arguments=KernelArguments(settings),
    )
    response = await agent.get_response("Read the last 5 messages in channel X of team Y.")
    print(response.content)

asyncio.run(run())
```

#### Architecture Notes

- **Kernel** is the dependency injection container — holds services (LLMs) and plugins (tools)
- **ChatCompletionAgent** is the high-level agent class; orchestration is done by SK via native function calling
- Supports OpenAPI plugins (auto-import from spec), MCP server plugins, and native code plugins
- Kernel can expose itself as an MCP server for other agents
- `GroupChatOrchestration` enables multi-agent patterns with `RoundRobinGroupChatManager`
- Fully local execution; no cloud process manager required
- Python 3.10+

#### Pros

- Officially backed by Microsoft — deepest alignment with Azure AI Foundry/M365 roadmap
- Plugin model integrates well with dependency injection (pass HTTP clients, tokens into constructor)
- MCP server compatibility (export plugins as MCP, consume MCP tools)
- Stable v1 API with commitment to non-breaking changes
- Moving to Microsoft Agent Framework 1.0 with A2A protocol support

#### Cons

- Async-only design for agents (requires `asyncio`) — slightly more boilerplate for simple scripts
- More concepts to learn: Kernel, KernelFunction, Plugins, ChatHistory, ExecutionSettings
- Python ecosystem smaller than LangChain's; fewer community blog posts
- `semantic-kernel` package is heavier; installs many Microsoft connectors

---

### 3. AutoGen (Microsoft)

#### Package Setup

```bash
pip install "autogen-agentchat" "autogen-ext[openai,azure]"
# Python 3.10+ required
```

Current stable: `autogen-agentchat` 0.7.5 (Sep 2025)

#### Azure AI Foundry LLM Integration

**Azure OpenAI (via deployment):**

```python
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.auth.azure import AzureTokenProvider
from azure.identity import DefaultAzureCredential

token_provider = AzureTokenProvider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

model_client = AzureOpenAIChatCompletionClient(
    azure_deployment="gpt-4o",
    model="gpt-4o",
    api_version="2024-06-01",
    azure_endpoint="https://{resource}.openai.azure.com/",
    azure_ad_token_provider=token_provider,
)
```

**Azure AI Foundry models (non-Azure-OpenAI, via `azure-ai-inference`):**

```python
from autogen_ext.models.azure import AzureAIChatCompletionClient
from azure.core.credentials import AzureKeyCredential

client = AzureAIChatCompletionClient(
    model="Phi-4",
    endpoint="https://{resource}.services.ai.azure.com/models",
    credential=AzureKeyCredential("your-api-key"),
    model_info={
        "json_output": True,
        "function_calling": True,
        "vision": False,
        "family": "phi",
        "structured_output": True,
    },
)
```

#### Custom Tool Definition (Teams API)

Tools are plain Python **async functions** — no decorator needed:

```python
import asyncio
import aiohttp
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console

async def read_teams_messages(team_id: str, channel_id: str, limit: int = 10) -> str:
    """Read recent messages from a Microsoft Teams channel.
    
    Args:
        team_id: The Teams group/team ID.
        channel_id: The channel ID within the team.
        limit: Maximum number of messages to return (default 10).
    
    Returns:
        Formatted string of recent messages.
    """
    token = await get_graph_token_async()
    async with aiohttp.ClientSession() as session:
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
        async with session.get(url, headers={"Authorization": f"Bearer {token}"}, params={"$top": limit}) as resp:
            resp.raise_for_status()
            data = await resp.json()
    return "\n".join(
        f"[{m['createdDateTime']}] {m['from']['user']['displayName']}: {m['body']['content']}"
        for m in data.get("value", [])
    )

async def send_teams_message(team_id: str, channel_id: str, message: str) -> str:
    """Send a message to a Microsoft Teams channel.
    
    Args:
        team_id: The Teams group/team ID.
        channel_id: The channel ID.
        message: The message text to send.
    
    Returns:
        Confirmation string with message ID.
    """
    token = await get_graph_token_async()
    async with aiohttp.ClientSession() as session:
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
        payload = {"body": {"contentType": "text", "content": message}}
        async with session.post(url, json=payload, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }) as resp:
            resp.raise_for_status()
            data = await resp.json()
    return f"Message sent. ID: {data['id']}"

# Create the agent
agent = AssistantAgent(
    name="teams_agent",
    model_client=model_client,
    tools=[read_teams_messages, send_teams_message],
    system_message="You are a Teams assistant. Use tools to read and write messages.",
    reflect_on_tool_use=True,  # Agent reasons about tool results before responding
)

async def main():
    await Console(agent.run_stream(task="Read the latest 5 messages from #general"))
    await model_client.close()

asyncio.run(main())
```

#### Architecture Notes

- AutoGen uses an **async-first** design — all agent interactions are coroutines
- Tool functions can be sync or async — sync functions are automatically wrapped
- `reflect_on_tool_use=True` causes the agent to generate a final summary after tool calls (recommended)
- `AssistantAgent` handles the full ReAct loop: call model → call tools → feed results back → repeat
- `autogen-core` provides event-driven multi-agent patterns for advanced scenarios
- `MCPWorkbench` extension allows consuming any MCP server as tools
- Fully local execution — no Azure orchestration required

#### Pros

- Very clean tool definition — plain Python functions with docstrings
- Strong Azure AI Foundry support via dedicated `AzureAIChatCompletionClient`
- Semantic Kernel adapter: can use SK model clients inside AutoGen
- MCP server support out of the box
- Excellent for multi-agent orchestration scenarios
- Actively maintained by Microsoft Research

#### Cons

- Async-first: `asyncio.run()` required even for simple scripts
- autogen-agentchat 0.7.5 released Sep 2025; no newer release in ~8 months (slower cadence than LangChain)
- 0.2 → 0.4 migration was a complete rewrite — risk of another breaking change
- Fewer tutorials for Teams/Graph API integration specifically

---

### 4. Azure AI Agents Service (Foundry Agent Service)

#### What It Is

The **Foundry Agent Service** is a **fully managed, cloud-hosted** orchestration platform for AI agents in Azure. It is NOT a local Python framework — it is a service you deploy to.

Source: https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview (Updated Apr 28, 2026)

#### Agent Types

| Type | Code Required | Hosting | Best For |
|---|---|---|---|
| **Prompt agents** | No | Fully managed | Rapid prototyping, simple tasks |
| **Workflow agents** (preview) | No (YAML optional) | Fully managed | Multi-step automation, branching |
| **Hosted agents** (preview) | Yes | Container-based | Custom logic, full control |

#### SDK

```bash
pip install "azure-ai-projects>=2.0.0"
```

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

project_client = AIProjectClient(
    endpoint="https://{resource-name}.services.ai.azure.com/api/projects/{project-name}",
    credential=DefaultAzureCredential()
)

# Get an OpenAI-compatible client from the project
with project_client.get_openai_client() as openai_client:
    response = openai_client.responses.create(
        model="gpt-4o",
        input="Summarize the latest Teams messages.",
    )
```

#### Integration with LangChain (via `langchain-azure-ai`)

The `AgentServiceFactory` in `langchain-azure-ai` lets you add a cloud-hosted Foundry agent as a **node in a LangGraph graph**:

```python
from langchain_azure_ai.agents import AgentServiceFactory
from azure.identity import DefaultAzureCredential

factory = AgentServiceFactory(
    project_endpoint="https://{resource}.services.ai.azure.com/api/projects/{project}",
    credential=DefaultAzureCredential()
)

# This node calls the cloud agent and returns results into your local graph
foundry_node = factory.get_agent_node(name="my-foundry-agent", version="latest")
graph.add_node("foundry_step", foundry_node)
```

#### Publishing to Teams

Foundry Agent Service has native publishing to **Microsoft Teams and Microsoft 365 Copilot** — this is the only framework option that natively distributes agents to Teams users without writing a Bot Framework / Graph API integration.

#### Can It Run Locally?

**Partially.** The runtime is cloud-hosted. You can:
- Call it from local Python via SDK
- Develop and test locally in the playground
- Use Hosted agents (containers) for more control

But the orchestration loop runs in Azure, not locally.

#### Pros

- Enterprise-grade: scaling, identity, RBAC, content safety, observability all built in
- Only option with native Teams/M365 Copilot distribution
- MCP server support for custom tools (Azure Functions webhook endpoint)
- Built-in versioning, tracing, evaluation
- Works with LangChain, LangGraph via `langchain-azure-ai`

#### Cons

- **NOT a local execution option** — this is a cloud service
- Requires Azure subscription and resource provisioning
- Custom tools must be hosted as MCP servers (extra infrastructure)
- For this use case (local Python process calling Teams), this is the wrong abstraction level
- Hosted agents (preview) add container deployment complexity

---

### 5. Custom Agent Loop (No Framework)

#### Pattern

```python
import json
import requests
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# --- Azure AI Foundry LLM setup ---
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)
client = AzureOpenAI(
    azure_endpoint="https://{resource}.openai.azure.com/",
    azure_ad_token_provider=token_provider,
    api_version="2024-06-01"
)

# --- Tool definitions (JSON schema for the model) ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "read_teams_messages",
            "description": "Read recent messages from a Microsoft Teams channel",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string", "description": "The Teams group ID"},
                    "channel_id": {"type": "string", "description": "The channel ID"},
                    "limit": {"type": "integer", "description": "Max messages", "default": 10}
                },
                "required": ["team_id", "channel_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_teams_message",
            "description": "Send a message to a Microsoft Teams channel",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string"},
                    "channel_id": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["team_id", "channel_id", "message"]
            }
        }
    }
]

# --- Tool implementations ---
def read_teams_messages(team_id: str, channel_id: str, limit: int = 10) -> str:
    token = get_graph_token()
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params={"$top": limit})
    resp.raise_for_status()
    msgs = resp.json().get("value", [])
    return "\n".join(f"[{m['createdDateTime']}] {m['from']['user']['displayName']}: {m['body']['content']}" for m in msgs)

def send_teams_message(team_id: str, channel_id: str, message: str) -> str:
    token = get_graph_token()
    resp = requests.post(
        f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages",
        json={"body": {"contentType": "text", "content": message}},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    resp.raise_for_status()
    return f"Sent. ID: {resp.json()['id']}"

TOOL_MAP = {
    "read_teams_messages": read_teams_messages,
    "send_teams_message": send_teams_message,
}

# --- Agent loop ---
def run_agent(user_message: str, max_iterations: int = 10) -> str:
    messages = [
        {"role": "system", "content": "You are a Teams assistant."},
        {"role": "user", "content": user_message}
    ]
    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_unset=True))

        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                result = TOOL_MAP[fn_name](**fn_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        else:
            # No more tool calls — final answer
            return msg.content

    return "Max iterations reached."

# Run it
print(run_agent("What are the last 3 messages in #general of my team?"))
```

#### When to Use This

Use a custom loop when:
- The agent has only 2–4 tools and simple, predictable patterns
- You want zero external dependencies beyond `openai`/`azure-ai-inference`
- The team is unfamiliar with frameworks and wants full transparency
- Performance is critical and you want to minimize indirection

#### Pros

- No framework dependencies — only `openai` or `azure-ai-inference`
- Complete transparency: every line is yours
- Easy to debug
- Maximum control over prompting, retries, error handling

#### Cons

- You build error handling, retries, conversation management yourself
- No streaming, structured output, middleware, or tracing out of the box
- Does not scale to complex multi-step reasoning or multi-tool scenarios well
- Adding features (memory, human-in-loop, multi-agent) requires significant code

---

## Microsoft Graph / Teams Tool Patterns

Regardless of which framework you choose, the Teams integration uses the same Microsoft Graph API calls:

### Authentication

```python
# Option A: Application permissions (daemon/background process)
from msal import ConfidentialClientApplication

app = ConfidentialClientApplication(
    client_id="YOUR_APP_ID",
    client_credential="YOUR_CLIENT_SECRET",
    authority=f"https://login.microsoftonline.com/{TENANT_ID}"
)
result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
token = result["access_token"]

# Option B: Delegated permissions (on-behalf-of a user)
# Use MSAL device flow or interactive auth — better for reading user-specific data
```

### Required Microsoft Graph Permissions

| Operation | Permission (Application) | Permission (Delegated) |
|---|---|---|
| Read channel messages | `ChannelMessage.Read.All` | `ChannelMessage.Read.All` |
| Send channel messages | `ChannelMessage.Send` | `ChannelMessage.Send` |
| List teams | `Team.ReadBasic.All` | `Team.ReadBasic.All` |
| List channels | `Channel.ReadBasic.All` | `Channel.ReadBasic.All` |

### Key API Endpoints

```
GET  /v1.0/teams/{teamId}/channels/{channelId}/messages?$top=10
POST /v1.0/teams/{teamId}/channels/{channelId}/messages
GET  /v1.0/me/joinedTeams
GET  /v1.0/teams/{teamId}/channels
```

---

## Final Recommendation

### Recommended Framework: **LangChain with `langchain-azure-ai`**

**Rationale:**

1. **Best Azure AI Foundry integration:** `langchain-azure-ai` 1.2.3 (Apr 2026) is a Microsoft-maintained package providing first-class support for Foundry models, the Foundry Agent Service, Azure AI Search, content safety, and OpenTelemetry tracing — all in one package. `AzureAIOpenAIApiChatModel` supports the new v1 API endpoint which serves all Foundry-hosted models (OpenAI, Mistral, Phi, Llama, DeepSeek) through a single interface.

2. **Simplest tool definition for the use case:** The `@tool` decorator requires only a function with a descriptive docstring. Adding Teams read/write as tools is three lines of code per tool. No class hierarchy, no decorators with metadata, no schema duplication.

3. **Largest ecosystem and community:** The most StackOverflow answers, GitHub issues, tutorials, and examples. If something goes wrong with the Teams integration or Azure auth, you will find answers faster.

4. **Fully local execution:** `create_agent` (backed by LangGraph) runs entirely in-process. No Azure orchestration service, no container, no port.

5. **Future-proof:** `langchain-azure-ai` supports using Foundry-hosted agents as LangGraph nodes — if you later want to offload some reasoning to Foundry Agent Service, you can add it without rewriting your graph.

6. **Active development:** `langchain-azure-ai` 1.2.3 was released April 23, 2026 (3 weeks before this research). It specifically addressed Foundry V2 API, content safety middleware, and Azure Application Insights tracing.

### Second Choice: **Semantic Kernel / Microsoft Agent Framework**

If your organization is standardizing on the Microsoft stack and wants the best long-term alignment with Azure AI Foundry, M365, and the A2A protocol, choose Semantic Kernel. The `@kernel_function` plugin model is excellent for Teams integration because it allows injecting the Graph token provider via the plugin constructor. The rebranding to Microsoft Agent Framework 1.0 means it has a committed stable API.

Choose SK/MAF over LangChain if:
- You plan to publish agents to Teams/M365 Copilot (Foundry Agent Service + MAF is the supported path)
- Your team is already familiar with Microsoft SDK patterns
- You want enterprise-grade multi-agent orchestration with the A2A protocol

### Third Choice: **AutoGen**

AutoGen is excellent but the async-first design adds friction for a simple local script. Choose it if you anticipate multi-agent scenarios (e.g., a "triage agent" delegating to a "Teams reader agent" and a "summarizer agent").

### When to Use Custom Loop

Only if: the agent has ≤4 tools, the logic is simple, and the team prefers zero framework dependencies.

### Do NOT Use: Foundry Agent Service (alone)

For a local Python process making Teams calls, the Foundry Agent Service is the wrong abstraction. It requires cloud infrastructure, hosted tool endpoints, and the orchestration loop runs in Azure. Use it as a complementary service (via `AgentServiceFactory` in LangChain) if you later need cloud-scale, Teams distribution, or built-in evaluation.

---

## Recommended Stack for This Project

```
azure-ai-projects>=2.0.0    # Foundry project client (optional)
langchain>=1.2              # Core agent framework
langchain-openai            # AzureChatOpenAI / ChatOpenAI v1
langchain-azure-ai>=1.2     # AzureAIOpenAIApiChatModel + tracing
azure-identity              # DefaultAzureCredential
msgraph-sdk                 # Microsoft Graph Python SDK (alternative to raw requests)
msal                        # Token acquisition for Graph API
```

---

## References

- Azure AI Foundry SDKs and Endpoints: https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/sdk-overview
- Foundry Agent Service overview: https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview
- LangChain AzureChatOpenAI integration: https://docs.langchain.com/oss/python/integrations/chat/azure_chat_openai
- LangChain Agents: https://docs.langchain.com/oss/python/langchain/agents
- langchain-azure-ai PyPI: https://pypi.org/project/langchain-azure-ai/
- Semantic Kernel Python README: https://github.com/microsoft/semantic-kernel/tree/main/python
- Semantic Kernel Plugins: https://learn.microsoft.com/en-us/semantic-kernel/concepts/plugins/
- AutoGen stable docs: https://microsoft.github.io/autogen/stable/
- AutoGen Models (Azure AI Foundry): https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/models.html
- autogen-agentchat PyPI 0.7.5: https://pypi.org/project/autogen-agentchat/
- Microsoft Agent Framework blog: https://devblogs.microsoft.com/agent-framework/semantic-kernel-and-microsoft-agent-framework/
