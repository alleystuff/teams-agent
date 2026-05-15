<!-- markdownlint-disable-file -->
# Implementation Details: Teams LLM Agent with Azure AI Foundry

## Context Reference

Sources: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` — full code samples, authentication
patterns, app registration steps, package list, and framework selection rationale.

---

## Implementation Phase 1: Project Scaffolding

<!-- parallelizable: true -->

### Step 1.1: Create requirements.txt

Create `requirements.txt` at the workspace root listing all Python package dependencies.

Files:
* `/Users/alimurad/Desktop/projects/teams-agent/requirements.txt` — Python package dependencies

Content:

```text
# Azure AI Foundry + identity
azure-ai-inference
azure-ai-projects>=2.1.0
azure-identity

# Agent framework
langchain
langchain-azure-ai
langchain-openai

# Microsoft Graph / Teams
msgraph-sdk

# Utilities
python-dotenv
```

Success criteria:
* File exists at workspace root
* `pip install -r requirements.txt` completes without errors

Context references:
* `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (pip Packages Required section) — package list

Dependencies:
* None

### Step 1.2: Create .env.template

Create `.env.template` at the workspace root as a reference for required environment variables. The developer
copies this to `.env` and fills in real values before running the agent.

Files:
* `/Users/alimurad/Desktop/projects/teams-agent/.env.template` — environment variable template

Content:

```dotenv
# ─── Azure AI Foundry ──────────────────────────────────────────────────────────
# Standard deployment (GPT-4o, GPT-4.1) — uses DefaultAzureCredential (az login)
AZURE_AI_ENDPOINT=https://<your-foundry-resource>.openai.azure.com/

# Serverless API endpoint (Llama, Phi-4, Mistral) — API key auth (uncomment to use)
# AZURE_INFERENCE_ENDPOINT=https://<host>.<region>.models.ai.azure.com
# AZURE_INFERENCE_CREDENTIAL=<api-key>

# Model deployment name and API version
AZURE_AI_DEPLOYMENT=gpt-4o
AZURE_AI_API_VERSION=2024-06-01

# ─── Microsoft Teams / Graph API ───────────────────────────────────────────────
# From your Entra app registration (see README.md for setup steps)
TEAMS_CLIENT_ID=<application-client-id>
TEAMS_TENANT_ID=<directory-tenant-id>
```

Success criteria:
* File exists at workspace root
* All required keys present as placeholders
* Comments explain Standard vs. Serverless deployment options

Context references:
* `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (.env Template section) — base content

Dependencies:
* None

### Step 1.3: Create tools/__init__.py

Create the `tools/` directory and an empty `__init__.py` to mark it as a Python package.

Files:
* `/Users/alimurad/Desktop/projects/teams-agent/tools/__init__.py` — empty package marker

Content: Empty file (zero bytes or single trailing newline).

Success criteria:
* `tools/` directory exists
* `from tools.teams_read import read_channel_messages` resolves after Step 3.1 completes

Dependencies:
* None

### Step 1.4: Create .gitignore

Create `.gitignore` at the workspace root to exclude `.env` and Python artifacts from version control.
This is a security baseline that prevents accidental credential commits (OWASP A02: Sensitive Data Exposure).

Files:
* `/Users/alimurad/Desktop/projects/teams-agent/.gitignore` — version control exclusion rules

Content:

```text
# Credentials — never commit
.env

# Python artifacts
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.venv/
```

Success criteria:
* `.gitignore` exists at workspace root
* `.env` is listed so `git status` does not show it as an untracked file

Context references:
* OWASP A02 (Sensitive Data Exposure) — baseline credential security

Dependencies:
* None

### Step 1.5: Validate phase

Validation commands:
* `pip install -r requirements.txt` — verify all packages resolve and install cleanly
* `python -c "import azure.ai.inference, azure.identity, langchain, msgraph; print('imports OK')"` — quick smoke test

---

## Implementation Phase 2: Authentication Module

<!-- parallelizable: false -->

### Step 2.1: Create auth.py

Create `auth.py` at the workspace root. Provides two public functions:

1. `get_foundry_credential()` — returns `DefaultAzureCredential` for Azure AI Foundry
2. `get_graph_client()` — returns a singleton `GraphServiceClient` using `DeviceCodeCredential`

The singleton pattern (via `_graph_client` module-level variable) ensures that device code authentication
triggers only once per process, even when both tool modules import `get_graph_client()`.

This deviates from the research sample code (which creates a new client per call) to prevent duplicate
device-code prompts at startup. See DD-01 in `.copilot-tracking/plans/logs/2026-05-13/teams-llm-agent-log.md`.

Files:
* `/Users/alimurad/Desktop/projects/teams-agent/auth.py` — credential factories

Content:

```python
import os
from azure.identity import DefaultAzureCredential, DeviceCodeCredential
from msgraph import GraphServiceClient

_graph_client: GraphServiceClient | None = None


def get_foundry_credential() -> DefaultAzureCredential:
    """Returns Azure credential for AI Foundry (requires az login or managed identity)."""
    return DefaultAzureCredential()


def get_graph_client() -> GraphServiceClient:
    """Returns a singleton Graph client using device code flow (delegated auth).

    Triggers interactive device code authentication once per process on first call.
    Subsequent calls return the cached instance without re-authenticating.

    Requires environment variables:
        TEAMS_CLIENT_ID: Entra application (client) ID
        TEAMS_TENANT_ID: Entra directory (tenant) ID
    """
    global _graph_client
    if _graph_client is None:
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
        _graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
    return _graph_client
```

Discrepancy references:
* DD-01: Singleton pattern deviates from research sample that creates a new client per call

Success criteria:
* `python -c "from auth import get_foundry_credential, get_graph_client; print('auth OK')"` passes
* No import errors for `azure.identity` or `msgraph`

Context references:
* `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (auth.py — Credential Setup section) — base code, adapted to singleton

Dependencies:
* Phase 1 complete (packages installed, `.env` populated)
* `TEAMS_CLIENT_ID` and `TEAMS_TENANT_ID` set in `.env`

### Step 2.2: Validate phase

Validation commands:
* `python -c "from auth import get_foundry_credential, get_graph_client; print('auth OK')"` — confirm no import errors
* Confirm no `ModuleNotFoundError` for `azure.identity` or `msgraph`

---

## Implementation Phase 3: Teams Tools

<!-- parallelizable: true -->

### Step 3.1: Create tools/teams_read.py

Create `tools/teams_read.py` with a LangChain `@tool`-decorated function that reads recent messages from
a Teams channel. The module-level `graph = get_graph_client()` call uses the singleton from `auth.py`.
`asyncio.run()` bridges the async Graph SDK to the synchronous LangChain tool interface.

Files:
* `/Users/alimurad/Desktop/projects/teams-agent/tools/teams_read.py` — read_channel_messages tool

Content:

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
        result = await graph.teams.by_team_id(team_id) \
            .channels.by_channel_id(channel_id) \
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

Discrepancy references:
* None — matches research exactly (singleton handled in auth.py)

Success criteria:
* `python -c "from tools.teams_read import read_channel_messages; print('read tool OK')"` passes
* `read_channel_messages` has `.name` and `.description` attributes (LangChain tool)

Context references:
* `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (tools/teams_read.py — Read Tool section) — exact code

Dependencies:
* Phase 2 (auth.py with singleton `get_graph_client()`)
* Phase 1 (tools/__init__.py, packages installed)

### Step 3.2: Create tools/teams_write.py

Create `tools/teams_write.py` with a LangChain `@tool`-decorated function that posts a plain-text message
to a Teams channel. Reuses the singleton `graph` client from `auth.py`. Returns the created message ID.

Files:
* `/Users/alimurad/Desktop/projects/teams-agent/tools/teams_write.py` — post_channel_message tool

Content:

```python
import asyncio
from langchain_core.tools import tool
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
        result = await graph.teams.by_team_id(team_id) \
            .channels.by_channel_id(channel_id) \
            .messages.post(body)
        return result.id
    return asyncio.run(_post())
```

Discrepancy references:
* None — matches research exactly (singleton handled in auth.py)
* Unused `MessagesRequestBuilder` import present in research sample omitted — the import is never referenced in the implementation and the Graph SDK does not require it for `messages.post()`

Success criteria:
* `python -c "from tools.teams_write import post_channel_message; print('write tool OK')"` passes
* `post_channel_message` has `.name` and `.description` attributes (LangChain tool)

Context references:
* `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (tools/teams_write.py — Write Tool section) — exact code

Dependencies:
* Phase 2 (auth.py with singleton `get_graph_client()`)
* Phase 1 (tools/__init__.py, packages installed)

---

## Implementation Phase 4: Main Agent

<!-- parallelizable: false -->

### Step 4.1: Create agent.py

Create `agent.py` at the workspace root. This is the sole entry point. It:

1. Loads `.env` via `python-dotenv`
2. Instantiates `AzureAIOpenAIApiChatModel` pointed at the Foundry deployment
3. Registers both Teams tools
4. Creates a LangChain tool-calling agent with a Teams-aware system prompt
5. Runs a blocking REPL loop until the user types `exit` or `quit`

Note: `AZURE_AI_DEPLOYMENT` and `AZURE_AI_API_VERSION` are read from `.env` (with sensible defaults),
rather than hardcoded as in the research sample. See DD-02 in `.copilot-tracking/plans/logs/2026-05-13/teams-llm-agent-log.md`.

Files:
* `/Users/alimurad/Desktop/projects/teams-agent/agent.py` — main agent entry point

Content:

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Must be called before tool imports; tools execute get_graph_client() at module level

from langchain_azure_ai import AzureAIOpenAIApiChatModel
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools.teams_read import read_channel_messages
from tools.teams_write import post_channel_message

llm = AzureAIOpenAIApiChatModel(
    endpoint=os.environ["AZURE_AI_ENDPOINT"],
    deployment_name=os.environ.get("AZURE_AI_DEPLOYMENT", "gpt-4o"),
    api_version=os.environ.get("AZURE_AI_API_VERSION", "2024-06-01"),
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

Discrepancy references:
* DD-02: `deployment_name` and `api_version` read from env vars; research hardcodes `"gpt-4o"` and version string
* DD-03: `load_dotenv()` moved before tool imports; research sample calls it after imports (which causes `KeyError` because tool modules read env vars at module load time)

Success criteria:
* `python agent.py` starts without import errors
* Device code flow prompts once at startup (from `get_graph_client()` singleton)
* LLM responds to natural-language prompts
* `exit` or `quit` terminates the loop cleanly

Context references:
* `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (agent.py — Main Agent section) — base code

Dependencies:
* Phase 2 (auth.py)
* Phase 3 (tools/teams_read.py, tools/teams_write.py)
* `.env` populated with `AZURE_AI_ENDPOINT`, `AZURE_AI_DEPLOYMENT`, `TEAMS_CLIENT_ID`, `TEAMS_TENANT_ID`

---

## Implementation Phase 5: Documentation

<!-- parallelizable: true -->

### Step 5.1: Create README.md

Create `README.md` at the workspace root. Target audience: a developer with an Azure subscription and
M365 tenant who wants to run the agent locally from scratch.

Files:
* `/Users/alimurad/Desktop/projects/teams-agent/README.md` — project documentation

Sections to include:

1. Overview — one paragraph: what the agent does, what LLM it uses, why device code
2. Prerequisites — Python 3.11+, Azure subscription + AI Foundry deployed model, M365 / Teams tenant, `az login`
3. Installation — `git clone` or copy, then `pip install -r requirements.txt`
4. App Registration (step-by-step from research):
   * New registration in Entra admin center
   * Allow public client flows = Yes (required for device code)
   * API permissions: `Team.ReadBasic.All`, `Channel.ReadBasic.All`, `ChannelMessage.Read.All` (admin consent), `ChannelMessage.Send`
   * Copy Client ID → `TEAMS_CLIENT_ID`, Tenant ID → `TEAMS_TENANT_ID`
5. Environment Configuration — copy `.env.template` → `.env`, fill in values
6. Running — `python agent.py`, what to expect (device code prompt, then REPL)
7. Project Structure — annotated file tree
8. Extending — suggested tools: `list_teams`, `list_channels`; upgrade path to Semantic Kernel

Success criteria:
* README.md exists at workspace root
* App registration steps match research document exactly
* A new developer can follow README from zero to a running agent

Context references:
* `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (App Registration Steps section) — exact steps
* `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Scenario A — Preferred Approach file tree) — project structure

Dependencies:
* Phases 1–4 complete (for accurate file names and command references)

---

## Implementation Phase 6: Validation

<!-- parallelizable: false -->

### Step 6.1: Run full project validation

Execute all validation commands:

```bash
# Install packages
pip install -r requirements.txt

# Verify AzureAIOpenAIApiChatModel class name (CRITICAL — class name from research is unverified)
python -c "import langchain_azure_ai; print([x for x in dir(langchain_azure_ai) if 'Azure' in x])"
# Expected output includes 'AzureAIOpenAIApiChatModel'. If absent, update agent.py with the correct class.
# Likely alternatives: AzureAIInferenceChatModel (AI Inference endpoint) or use AzureChatOpenAI from langchain_openai

# Import checks (run from workspace root after populating .env)
python -c "from auth import get_foundry_credential, get_graph_client; print('auth OK')"
python -c "from tools.teams_read import read_channel_messages; print('read tool OK')"
python -c "from tools.teams_write import post_channel_message; print('write tool OK')"
python -c "import agent; print('agent module OK')"
```

### Step 6.2: Fix minor validation issues

Iterate on import errors, version conflicts, or missing env vars. Apply fixes directly when straightforward.

Common issues and resolutions:
* `ImportError: cannot import name 'AzureAIOpenAIApiChatModel'` — the class name from the research document is unverified; run the class discovery command in Step 6.1 and update `agent.py` with the correct name (see DR-06 in planning log)
* `ModuleNotFoundError: langchain_azure_ai` — check package name with `pip show langchain-azure-ai`; class may be under a sub-path
* `KeyError: TEAMS_CLIENT_ID` — ensure `.env` is populated and in the workspace root where `load_dotenv()` will find it
* `asyncio.run() cannot be called when another event loop is running` — only an issue in Jupyter; not relevant for script mode
* `DeviceCodeCredential` prompt not appearing — check that `TEAMS_CLIENT_ID`/`TEAMS_TENANT_ID` are correct and that the app registration has public client flows enabled

### Step 6.3: Report blocking issues

When validation failures require changes beyond minor fixes:
* Document the issues and affected files
* Provide the user with next steps
* Recommend additional research and planning rather than inline fixes

---

## Dependencies

* Python 3.11+
* Azure subscription with AI Foundry access and a deployed model (Standard or Serverless endpoint)
* Microsoft 365 / Teams tenant with a configured Entra app registration
* `az login` completed on the local machine (for `DefaultAzureCredential`)

## Success Criteria

* All source files created with correct content
* `pip install -r requirements.txt` succeeds
* All import checks pass without errors
* `python agent.py` starts and prompts for device code authentication
* Agent reads and posts to Teams channels end-to-end
