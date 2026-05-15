<!-- markdownlint-disable-file -->
# Task Research: LLM-Based Agent with Azure AI Foundry and Microsoft Teams Integration

An agent that uses an LLM deployed in Azure AI Foundry, runs locally, and can read and write messages to Microsoft Teams channels or chats.

## Task Implementation Requests

* Build a locally-running LLM agent that calls an Azure AI Foundry-deployed model
* Enable the agent to read messages from Microsoft Teams
* Enable the agent to write/post messages to Microsoft Teams
* Orchestrate agent behavior with tool use (Teams read/write as tools)

## Scope and Success Criteria

* Scope: Azure AI Foundry model integration, Microsoft Teams Graph API access, local agent runtime, authentication setup
* Assumptions:
  * Developer has an Azure subscription with AI Foundry access
  * Developer has a Microsoft 365 / Teams tenant with sufficient permissions to register an app
  * Agent runs as a local Python process (not deployed as a cloud service)
  * Developer (or a specific user) will authenticate interactively at startup (device code flow)
* Success Criteria:
  * Agent authenticates with Azure AI Foundry and calls an LLM
  * Agent reads messages from one or more Teams channels via Microsoft Graph API
  * Agent posts messages to Teams channels via Microsoft Graph API
  * End-to-end local execution works with a single `python agent.py` command

## Outline

1. Azure AI Foundry LLM integration (SDK, endpoint, auth)
2. Microsoft Teams messaging via Microsoft Graph API (read/write)
3. App registration and permission scopes for Teams access
4. Local agent framework selection — selected: LangChain + langchain-azure-ai
5. Authentication architecture: Foundry (DefaultAzureCredential) + Teams (DeviceCodeCredential)
6. Tool definitions wrapping Graph API calls
7. End-to-end implementation plan

## Research Executed

### External Research

**Azure AI Foundry SDK:**
- Source: [Azure AI Foundry Python quickstart](https://learn.microsoft.com/en-us/azure/ai-foundry/)
- Source: [azure-ai-inference PyPI](https://pypi.org/project/azure-ai-inference/)
- Source: [azure-sdk-for-python samples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/ai/azure-ai-inference)
- Subagent output: `.copilot-tracking/research/subagents/2026-05-13/azure-ai-foundry-research.md`

**Microsoft Graph API / Teams:**
- Source: [Microsoft Graph Teams API Overview](https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview)
- Source: [Graph SDK for Python](https://learn.microsoft.com/en-us/graph/sdks/sdk-installation#install-the-microsoft-graph-python-sdk)
- Source: [msgraph-sdk-python GitHub](https://github.com/microsoftgraph/msgraph-sdk-python)
- Subagent output: `.copilot-tracking/research/subagents/2026-05-13/teams-graph-api-research.md`

**Agent Frameworks:**
- Source: [LangChain Azure AI Docs](https://python.langchain.com/docs/integrations/llms/azure_openai)
- Source: [Semantic Kernel Python](https://github.com/microsoft/semantic-kernel/tree/main/python)
- Source: [AutoGen](https://microsoft.github.io/autogen/)
- Source: [Azure AI Foundry Agents](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview)
- Subagent output: `.copilot-tracking/research/subagents/2026-05-13/agent-frameworks-research.md`

## Key Discoveries

### Platform and Terminology (2026)

Azure AI Studio → Azure AI Foundry → now called **Microsoft Foundry** (2026 rebrand). Hub-based "classic" projects still work; new investment is in the Foundry resource model. The unified `azure-ai-projects` SDK (2.1.0 stable) wraps `azure-ai-inference` and adds tracing, eval, and agent service features.

### Azure AI Foundry Deployment Types

| Type | Best For | Auth | SDK |
|---|---|---|---|
| **Standard Deployment** | GPT-4o, GPT-4.1, o-series | Entra ID or API key | `azure-ai-inference` or `openai` |
| **Serverless API Endpoint** | Llama, Phi-4, Mistral, DeepSeek | **API key only** | `azure-ai-inference` |
| **Managed Compute** | Custom / HuggingFace models | Entra ID | `azure-ai-inference` + deployment header |

### Critical Teams Permission Constraint

**App-only credentials CANNOT post messages to Teams channels or chats.** Only `Teamwork.Migrate.All` exists as an application permission for posting, and it is migration-only. All regular posting requires a **delegated permission** (a signed-in user). This means the agent must authenticate on behalf of a user.

**Consequence:** The agent must use **device code flow** (`DeviceCodeCredential`) or interactive browser flow at startup. It cannot run as an unattended background daemon if it needs to post messages.

### Required Permissions for Teams

| Action | Permission | Type | Admin Consent |
|---|---|---|---|
| List joined teams | `Team.ReadBasic.All` | Delegated | No |
| List channels | `Channel.ReadBasic.All` | Delegated | No |
| Read channel messages | `ChannelMessage.Read.All` | Delegated | **Yes** |
| Post channel message | `ChannelMessage.Send` | Delegated | No |
| Read chat messages | `Chat.Read` | Delegated | No |
| Post chat message | `Chat.ReadWrite` | Delegated | No |

### Graph API Throttle Limits (Teams)

* GET channel messages: 20 rps/app, 1 rps/channel
* POST channel message: 50 rps/app, **1 rps/channel** (hard per-channel limit)

### Agent Framework Landscape (2026)

| Framework | Azure AI Foundry | Custom Tools | Local-Only | Maturity |
|---|---|---|---|---|
| **LangChain + langchain-azure-ai** | Native (`AzureAIOpenAIApiChatModel`) | `@tool` decorator | Yes | High, monthly releases |
| **Semantic Kernel / MAF 1.0** | Native | `@kernel_function` plugin | Yes | Stable LTS (Microsoft) |
| **AutoGen 0.7.5** | `AzureAIChatCompletionClient` | Plain async functions | Yes | Sep 2025, slower cadence |
| **Azure AI Foundry Agent Service** | Native | YAML/container | **No** (cloud) | Not applicable |
| **Custom loop** | Via `openai` SDK | Explicit JSON parsing | Yes | N/A |

### pip Packages Required

```bash
# LLM / Foundry
pip install azure-ai-inference azure-ai-projects azure-identity

# Agent framework
pip install langchain langchain-azure-ai langchain-openai

# Teams Graph API
pip install msgraph-sdk

# (optional) local secrets management
pip install python-dotenv
```

## Technical Scenarios

### Scenario A: LangChain + langchain-azure-ai (Selected)

**Description:** Use LangChain's `create_agent` with `langchain-azure-ai` connecting to an Azure AI Foundry model. Teams read/write are `@tool`-decorated Python functions calling the Microsoft Graph SDK. Authentication for the LLM uses `DefaultAzureCredential` (or API key). Authentication for Teams uses `DeviceCodeCredential` at startup.

**Requirements:**
* Azure AI Foundry project with a deployed model (Standard or Serverless endpoint)
* Microsoft Entra app registration with delegated Teams permissions
* Python 3.11+
* `az login` completed (for DefaultAzureCredential on Foundry)

**Preferred Approach:**

```text
teams-agent/
├── .env                   # AZURE_AI_ENDPOINT, TEAMS_CLIENT_ID, TEAMS_TENANT_ID
├── requirements.txt
├── agent.py               # main entry point — assembles agent and runs REPL
├── auth.py                # credential factories for Foundry + Graph
├── tools/
│   ├── __init__.py
│   ├── teams_read.py      # @tool: list_channels, read_channel_messages
│   └── teams_write.py     # @tool: post_channel_message
└── README.md
```

**Implementation Details:**

#### auth.py — Credential Setup

```python
import os
from azure.identity import DefaultAzureCredential, DeviceCodeCredential
from msgraph import GraphServiceClient

def get_foundry_credential():
    """Returns Azure credential for AI Foundry (requires az login)."""
    return DefaultAzureCredential()

def get_graph_client() -> GraphServiceClient:
    """Returns Graph client using device code flow (delegated, for posting)."""
    credential = DeviceCodeCredential(
        client_id=os.environ["TEAMS_CLIENT_ID"],
        tenant_id=os.environ["TEAMS_TENANT_ID"],
    )
    scopes = [
        "https://graph.microsoft.com/Team.ReadBasic.All",
        "https://graph.microsoft.com/Channel.ReadBasic.All",
        "https://graph.microsoft.com/ChannelMessage.Read.All",
        "https://graph.microsoft.com/ChannelMessage.Send",
    ]
    return GraphServiceClient(credentials=credential, scopes=scopes)
```

#### tools/teams_read.py — Read Tool

```python
import asyncio
from langchain_core.tools import tool
from auth import get_graph_client

graph = get_graph_client()

@tool
def read_channel_messages(team_id: str, channel_id: str, top: int = 10) -> list[dict]:
    """Read the most recent messages from a Microsoft Teams channel.
    
    Args:
        team_id: The Teams team ID (GUID).
        channel_id: The channel ID (GUID).
        top: Number of recent messages to retrieve (default 10, max 50).
    
    Returns:
        List of dicts with 'from', 'body', 'createdDateTime' fields.
    """
    async def _fetch():
        result = await graph.teams.by_team_id(team_id)\
            .channels.by_channel_id(channel_id)\
            .messages.get(query_parameters={"$top": top})
        return [
            {
                "from": m.from_.user.display_name if m.from_ and m.from_.user else "unknown",
                "body": m.body.content if m.body else "",
                "createdDateTime": str(m.created_date_time),
            }
            for m in (result.value or [])
        ]
    return asyncio.run(_fetch())
```

#### tools/teams_write.py — Write Tool

```python
import asyncio
from langchain_core.tools import tool
from msgraph.generated.teams.item.channels.item.messages.messages_request_builder import MessagesRequestBuilder
from msgraph.generated.models.chat_message import ChatMessage
from msgraph.generated.models.item_body import ItemBody
from auth import get_graph_client

graph = get_graph_client()

@tool
def post_channel_message(team_id: str, channel_id: str, message: str) -> str:
    """Post a plain-text message to a Microsoft Teams channel.
    
    Args:
        team_id: The Teams team ID (GUID).
        channel_id: The channel ID (GUID).
        message: The plain-text message content to post.
    
    Returns:
        The ID of the created message.
    """
    async def _post():
        body = ChatMessage(body=ItemBody(content=message))
        result = await graph.teams.by_team_id(team_id)\
            .channels.by_channel_id(channel_id)\
            .messages.post(body)
        return result.id
    return asyncio.run(_post())
```

#### agent.py — Main Agent

```python
import os
from dotenv import load_dotenv
from langchain_azure_ai import AzureAIOpenAIApiChatModel
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools.teams_read import read_channel_messages
from tools.teams_write import post_channel_message

load_dotenv()

llm = AzureAIOpenAIApiChatModel(
    endpoint=os.environ["AZURE_AI_ENDPOINT"],  # e.g. https://<foundry>.openai.azure.com/
    deployment_name="gpt-4o",
    api_version="2024-06-01",
)

tools = [read_channel_messages, post_channel_message]

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant with access to Microsoft Teams. "
               "You can read messages and post to channels."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

if __name__ == "__main__":
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ("exit", "quit"):
            break
        response = executor.invoke({"input": user_input})
        print(f"\nAgent: {response['output']}")
```

#### .env Template

```dotenv
# Azure AI Foundry
AZURE_AI_ENDPOINT=https://<your-foundry-resource>.openai.azure.com/
# OR for API key auth (Serverless):
# AZURE_INFERENCE_ENDPOINT=https://<host>.<region>.models.ai.azure.com
# AZURE_INFERENCE_CREDENTIAL=<api-key>

# Microsoft Teams / Graph API (Entra app registration)
TEAMS_CLIENT_ID=<app-client-id>
TEAMS_TENANT_ID=<azure-ad-tenant-id>
```

#### App Registration Steps

1. Go to [Entra admin center](https://entra.microsoft.com) → App registrations → New registration
2. Name: `Teams LLM Agent (local dev)`, Single tenant
3. Redirect URI: Platform = **Mobile and desktop**, URI = `http://localhost`
4. Under Authentication → Advanced settings: **Allow public client flows = Yes** (required for device code)
5. Under API permissions → Add:
   - `Microsoft Graph` → Delegated → `Team.ReadBasic.All`, `Channel.ReadBasic.All`, `ChannelMessage.Read.All` (admin consent), `ChannelMessage.Send`
6. Click **Grant admin consent** for `ChannelMessage.Read.All`
7. Copy Application (client) ID → `TEAMS_CLIENT_ID`
8. Copy Directory (tenant) ID → `TEAMS_TENANT_ID`

#### Considered Alternatives

**Semantic Kernel / Microsoft Agent Framework 1.0**
- Best long-term fit if planning to publish agent to Teams/M365 Copilot later
- Uses `@kernel_function` plugins instead of `@tool` decorator — slightly more ceremony
- Stable LTS from Microsoft; aligned with A2A protocol roadmap
- Recommended if the project evolves toward multi-agent or M365 Copilot integration

Rejected for initial implementation because: LangChain has broader tooling, more examples, and `langchain-azure-ai` provides the same Foundry connectivity with less boilerplate.

**AutoGen 0.7.5**
- Has `AzureAIChatCompletionClient` for non-OpenAI Foundry models (Phi-4, Llama)
- Async-first adds friction for a simple local script
- Release cadence slowed (last release Sep 2025)
- Best fit if multi-agent orchestration is needed from the start

**Azure AI Foundry Agent Service**
- Fully managed cloud service — not a local runner
- Cannot satisfy the "runs locally" requirement without wrapping it as cloud sub-agents
- Appropriate only if deploying to production or publishing to Teams/M365 Copilot

**Custom Loop (no framework)**
- Minimal dependencies, maximum control
- Not worth the duplication for a project with >2 tools; tool dispatch, error handling, and multi-turn conversation all need hand-coding

**Teams Bot Framework vs. Graph API**
- Bot Framework: Richer Teams UX (cards, buttons, proactive messaging), but requires a public endpoint (ngrok/tunnel for local dev), complex registration
- **Graph API: Simpler auth, no public endpoint needed for local dev, sufficient for read/write messages.** Selected.

## Potential Follow-Up Research

* Delta query (`GET /chatmessage/delta`) — polling for new messages without a webhook, for a reactive agent pattern
* Using `devtunnel` or `ngrok` for local webhook subscriptions (event-driven alternative to polling)
* Resource-Specific Consent (RSC) with `ChannelMessage.Read.Group` — avoids tenant-wide admin consent for reading messages
* Posting adaptive cards via Graph API (`contentType: "html"` or `attachment` with card JSON)
* Extending the agent with additional tools: list teams, search messages, reply to thread, react with emoji
* Upgrading to Semantic Kernel / MAF if M365 Copilot publishing becomes a requirement
* Token caching for `DeviceCodeCredential` — avoid re-authenticating on every run
