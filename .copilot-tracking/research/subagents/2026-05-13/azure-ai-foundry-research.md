# Azure AI Foundry — LLM Deployment and Python SDK Integration

**Research Date:** 2026-05-13  
**Status:** Complete  
**Sources:** Microsoft Learn docs, PyPI package pages, GitHub azure-sdk-for-python samples

---

## Table of Contents

1. What is Azure AI Foundry (now Microsoft Foundry)?
2. Key Concepts and Resource Model
3. Deployment Options for LLMs
4. SDK Overview — Which Package to Use
5. `azure-ai-inference` Deep Dive
6. `azure-ai-projects` Deep Dive
7. Authentication Patterns
8. Code Examples
9. Package Versions and Install Commands
10. Gotchas and Important Notes

---

## 1. What is Azure AI Foundry (now Microsoft Foundry)?

**Microsoft Foundry** (formerly called Azure AI Studio → Azure AI Foundry) is a unified Azure platform-as-a-service for enterprise AI operations, model building, and application development. As of 2026, it has been rebranded to **Microsoft Foundry** with a new Foundry portal at https://ai.azure.com.

### Relationship to Azure OpenAI Service and Azure ML

| Concept | Previous Name | Current Name (2026) |
|---|---|---|
| Brand | Azure AI Studio / Azure AI Foundry | Microsoft Foundry |
| Brand | Azure AI Services | Foundry Tools |
| Portal | Foundry (classic) | Foundry |
| Agent API | Assistants API (Agents v0.5/v1) | Responses API (Agents v2) |
| API versioning | Monthly api-version params | v1 stable routes (/openai/v1/) |
| Resource model | Hub + Azure OpenAI + Azure AI Services | Foundry resource (single, with projects) |
| SDKs | Multiple packages (azure-ai-inference, azure-ai-generative, azure-ai-ml, AzureOpenAI()) against 5+ endpoints | Unified project client (azure-ai-projects 2.x) + OpenAI() against one project endpoint |

**Key relationships:**
- **Azure OpenAI Service** models (GPT-4o, GPT-4.1, o-series, etc.) are deployable through Foundry and still accessible via Azure OpenAI endpoints. Foundry adds orchestration, multi-model support, agents, evaluation, and fine-tuning on top.
- **Azure ML** managed compute is used for deploying open-source/community models (Hugging Face, NVIDIA NIMs, custom models) as Managed Compute endpoints. The Foundry portal replaced the Azure ML Studio UI for most model deployment workflows.
- **Serverless API endpoints** allow deploying Foundry Models (Llama, Mistral, Phi, etc.) on pay-as-you-go token billing without managing compute.

### Who it's for
- **Application developers** building AI-powered products with agents, models, and tools.
- **ML engineers** who fine-tune models, run evaluations, and manage model deployments.
- **IT administrators** governing AI resources and managing access across teams.

---

## 2. Key Concepts and Resource Model

### New Foundry Resource Model (2026)
- **Foundry Resource**: Single top-level Azure resource (replaces Hub + Azure OpenAI + Azure AI Services trio).
- **Project**: A workspace within a Foundry resource for organizing work. Endpoint format: `https://<resource_name>.ai.azure.com/api/projects/<project_name>`
- **Deployment**: A deployed instance of a model within the project.
- **Endpoint**: The URL used to call the deployed model.

### Classic Hub Model (still supported via Foundry Classic)
- **Hub**: The organizational container (like a workspace).
- **Project**: Lives inside a Hub. Has a connection string format.
- **Serverless API Endpoint**: Dedicated endpoint hosted inside an AI Hub project.
- **Managed Compute Endpoint**: Dedicated compute instance inside an AI Hub project.

> **Note:** Hub-based projects still work via `Foundry (classic)` portal and the 1.x SDKs. New investments focus on the new Foundry resource model.

---

## 3. Deployment Options for LLMs

Foundry provides three main deployment options:

### 3.1 Standard Deployment in Foundry Resources (Recommended)
- **Best for:** OpenAI models (GPT-4o, GPT-4.1, o-series, etc.) and flagship Foundry models.
- **Billing:** Token usage or Provisioned Throughput Units (PTU).
- **Data processing:** Regional, Data-zone, or Global.
- **Features:** Content filtering, custom content filtering, keyless (Entra ID) authentication.
- **Available in:** Foundry resources, Azure OpenAI resources, Azure AI Hub (when connected to Foundry resource).

### 3.2 Serverless API Endpoint
- **Best for:** Non-OpenAI models from the catalog: Llama, Mistral, Phi, DeepSeek, Cohere, etc.
- **Billing:** Pay-as-you-go token billing (minimal endpoint infrastructure billed per minute).
- **Data processing:** Regional only.
- **Authentication:** API Key only (no keyless/Entra ID).
- **Available in:** AI Hub resources (classic model) only.
- **Endpoint URL format:** `https://<your-host-name>.<your-azure-region>.models.ai.azure.com`

### 3.3 Managed Compute
- **Best for:** Models requiring dedicated compute — Hugging Face, NVIDIA NIMs, industry models (Bayer, Rockwell, etc.), Databricks, custom models.
- **Billing:** Per-minute compute core hours.
- **Authentication:** Entra ID or API key.
- **Available in:** AI Hub resources (classic model) only.
- **Required when deploying:** custom models and open-source models not in Serverless catalog.

### Supported Model Families (as of 2026)
- GPT-4.1, GPT-4.1 mini, GPT-5, GPT-5 mini (OpenAI)
- Claude (Anthropic)
- Grok (xAI)
- Mistral (Code, multilingual)
- DeepSeek-R1
- Phi-4 (Microsoft — small, on-device capable)
- Meta Llama (open-weight, fine-tunable)
- Hugging Face models (via Managed Compute)
- NVIDIA NIMs (via Managed Compute)

---

## 4. SDK Overview — Which Package to Use

There are three main Python package paths. Choosing the right one depends on your use case:

| Package | Version | Use When |
|---|---|---|
| `azure-ai-inference` | 1.0.0b9 (beta) | Direct model calls to Serverless API, Managed Compute, or Azure OpenAI endpoints. Lower-level, explicit endpoint. Works without a Foundry Project. Also works with GitHub Models. |
| `azure-ai-projects` + `openai` | 2.1.0 (stable) | Full Foundry Project integration: agents, evaluations, fine-tuning, model management. Uses the Foundry project endpoint and Responses API. |
| `openai` (official OpenAI SDK) | latest | Pure Azure OpenAI Service calls, or when using `azure-ai-projects.get_openai_client()`. Recommended for production Azure OpenAI usage. |

### `azure-ai-generative` (Deprecated/Legacy)
- This was a predecessor package. **Do not use for new projects.** Its functionality was moved into `azure-ai-projects` and other packages.

---

## 5. `azure-ai-inference` Deep Dive

**PyPI:** https://pypi.org/project/azure-ai-inference/  
**Latest version:** 1.0.0b9 (released Feb 14, 2025) — still in beta  
**REST API version used:** `2024-05-01-preview`

### Key Clients

| Client Class | Purpose | Route |
|---|---|---|
| `ChatCompletionsClient` | Chat completions | `/chat/completions` |
| `EmbeddingsClient` | Text embeddings | `/embeddings` |
| `ImageEmbeddingsClient` | Image embeddings | `/images/embeddings` |

All clients can be imported from `azure.ai.inference` (sync) or `azure.ai.inference.aio` (async).

### Supported Message Types
`SystemMessage`, `UserMessage`, `AssistantMessage`, `ToolMessage`, `DeveloperMessage`

### Key Method: `client.complete()`
```python
response = client.complete(
    messages=[...],
    tools=[...],          # optional: tool/function definitions
    stream=True,          # optional: enable streaming
    temperature=0.7,      # optional
    max_tokens=1000,      # optional
    model_extras={...},   # optional: model-specific extra params
)
```

### `load_client` Utility
Auto-detects and returns the right client based on endpoint URL. Works for Serverless API and Managed Compute endpoints only (not GitHub Models or Azure OpenAI).

```python
from azure.ai.inference import load_client
client = load_client(endpoint=endpoint, credential=AzureKeyCredential(key))
```

### `get_model_info()`
Returns model metadata (name, provider, type). Only works on Serverless API and Managed Compute endpoints.

---

## 6. `azure-ai-projects` Deep Dive

**PyPI:** https://pypi.org/project/azure-ai-projects/  
**Latest version:** 2.1.0 (released Apr 20, 2026) — stable  
**REST API version:** v1 of Microsoft Foundry data plane REST APIs

### Key Class: `AIProjectClient`
```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project_client = AIProjectClient(
    endpoint="https://<resource>.ai.azure.com/api/projects/<project>",
    credential=DefaultAzureCredential(),
)
```

> **Authentication note:** Only Entra ID (DefaultAzureCredential) is supported for AIProjectClient as of 2.x. API keys are not yet supported for the client constructor.

### Key Sub-clients and Operations

| Property / Method | Purpose |
|---|---|
| `.get_openai_client()` | Returns an authenticated OpenAI SDK client pointed at the Foundry project endpoint. Used for Responses API, chat, fine-tuning, evals, files. |
| `.agents` | Create, manage, and run Agents (Responses protocol). |
| `.beta.agents` | Preview agent operations (Sessions, patch_agent_details). |
| `.deployments` | List AI models deployed to the project. |
| `.connections` | List connected Azure resources. |
| `.datasets` | Upload and reference documents. |
| `.indexes` | Create/list Azure AI Search indexes. |
| `.telemetry` | Get Application Insights connection string for tracing. |
| `.beta.memory_stores` | Preview: agent memory management. |
| `.beta.red_teams` | Preview: red-team scanning. |
| `.evaluation_rules`, `.beta.evaluators`, `.beta.insights`, `.beta.schedules` | Evaluation operations. |

### Using the OpenAI Client via Projects
```python
with project_client.get_openai_client() as openai_client:
    response = openai_client.responses.create(
        model="gpt-4.1",  # deployment name in your Foundry project
        input="What is the capital of France?",
    )
    print(response.output_text)
```

### Creating an Agent
```python
from azure.ai.projects.models import PromptAgentDefinition

agent = project_client.agents.create_version(
    agent_name="MyAgent",
    definition=PromptAgentDefinition(
        model="gpt-4.1",
        instructions="You are a helpful assistant.",
    ),
)
```

---

## 7. Authentication Patterns

### Pattern A: API Key Authentication (`AzureKeyCredential`)
- Works with: `azure-ai-inference` for Serverless API and Managed Compute endpoints, and for Azure OpenAI endpoints.
- **Does NOT work** with: `azure-ai-projects` 2.x (no API key support in the new Foundry resource model).
- **Serverless API note:** Only API key authentication is supported for Serverless endpoints (no Entra ID).

```python
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference import ChatCompletionsClient

client = ChatCompletionsClient(
    endpoint="https://your-host.eastus2.models.ai.azure.com",
    credential=AzureKeyCredential("your-api-key"),
)
```

### Pattern B: DefaultAzureCredential (Entra ID / az login)
- Works with: `azure-ai-inference` for Managed Compute and Azure OpenAI endpoints; `azure-ai-projects` 2.x for Foundry resources.
- **Best for local development:** Run `az login` once, then `DefaultAzureCredential` picks it up automatically.
- Only Managed Compute endpoints and Azure OpenAI endpoints support Entra ID via `azure-ai-inference`.

```python
from azure.identity import DefaultAzureCredential
from azure.ai.inference import ChatCompletionsClient

client = ChatCompletionsClient(
    endpoint="https://your-resource.openai.azure.com/openai/deployments/gpt-4o",
    credential=DefaultAzureCredential(exclude_interactive_browser_credential=False),
    credential_scopes=["https://cognitiveservices.azure.com/.default"],
    api_version="2024-06-01",
)
```

### Pattern C: Interactive Browser / Device Code Flow
Set `exclude_interactive_browser_credential=False` in `DefaultAzureCredential()`. On local dev machines, if `az login` hasn't been run, this will open a browser window.

### Pattern D: ManagedIdentityCredential
Used in production Azure-hosted environments (App Service, AKS, etc.):
```python
from azure.identity import ManagedIdentityCredential
credential = ManagedIdentityCredential()
```

### Environment Variables (Common)

| Environment Variable | Used By | Purpose |
|---|---|---|
| `AZURE_AI_CHAT_ENDPOINT` | `azure-ai-inference` samples | Serverless/Managed Compute endpoint URL |
| `AZURE_AI_CHAT_KEY` | `azure-ai-inference` samples | API key for Serverless/Managed Compute |
| `AZURE_OPENAI_CHAT_ENDPOINT` | `azure-ai-inference` samples | Azure OpenAI deployment endpoint URL |
| `AZURE_OPENAI_CHAT_KEY` | `azure-ai-inference` samples | Azure OpenAI API key |
| `AZURE_AI_CHAT_DEPLOYMENT_NAME` | `azure-ai-inference` samples | Sets `azureml-model-deployment` header for Managed Compute |
| `FOUNDRY_PROJECT_ENDPOINT` | `azure-ai-projects` 2.x | Full Foundry project endpoint URL |
| `FOUNDRY_MODEL_NAME` | `azure-ai-projects` 2.x samples | Deployment name of model in Foundry project |
| `AZURE_AI_EMBEDDINGS_ENDPOINT` | `azure-ai-inference` | Embeddings endpoint |
| `AZURE_AI_EMBEDDINGS_KEY` | `azure-ai-inference` | Embeddings API key |

### Role Assignments Needed for Entra ID
For `DefaultAzureCredential` with Foundry resources, the user/service principal needs an appropriate RBAC role (e.g., "Azure AI Developer" or "Cognitive Services OpenAI User") assigned in the Azure portal on the project resource.

---

## 8. Code Examples

### 8.1 Minimal Chat Completion (azure-ai-inference, API Key, Serverless)
```python
import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

endpoint = os.environ["AZURE_AI_CHAT_ENDPOINT"]
key = os.environ["AZURE_AI_CHAT_KEY"]

client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(key))

response = client.complete(
    messages=[
        SystemMessage("You are a helpful assistant."),
        UserMessage("How many feet are in a mile?"),
    ],
)

print(response.choices[0].message.content)
print(f"Token usage: {response.usage}")
client.close()
```

### 8.2 Streaming Chat Completion (azure-ai-inference)
```python
import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

endpoint = os.environ["AZURE_AI_CHAT_ENDPOINT"]
key = os.environ["AZURE_AI_CHAT_KEY"]

client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(key))

response = client.complete(
    stream=True,
    messages=[
        SystemMessage("You are a helpful assistant."),
        UserMessage("Give me 5 good reasons why I should exercise every day."),
    ],
)

for update in response:
    if update.choices and update.choices[0].delta:
        print(update.choices[0].delta.content or "", end="", flush=True)
    if update.usage:
        print(f"\n\nToken usage: {update.usage}")

client.close()
```

### 8.3 Tool/Function Calling (azure-ai-inference)
```python
import os
import json
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import (
    AssistantMessage,
    ChatCompletionsToolDefinition,
    CompletionsFinishReason,
    FunctionDefinition,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from azure.core.credentials import AzureKeyCredential

endpoint = os.environ["AZURE_AI_CHAT_ENDPOINT"]
key = os.environ["AZURE_AI_CHAT_KEY"]

def get_weather(city: str) -> str:
    """Mock weather lookup."""
    return json.dumps({"city": city, "temp_f": 72, "condition": "Sunny"})

weather_tool = ChatCompletionsToolDefinition(
    function=FunctionDefinition(
        name="get_weather",
        description="Returns current weather for a given city.",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
            },
            "required": ["city"],
        },
    )
)

client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(key))

messages = [
    SystemMessage("You are a weather assistant."),
    UserMessage("What is the weather in Seattle?"),
]

response = client.complete(messages=messages, tools=[weather_tool])

if response.choices[0].finish_reason == CompletionsFinishReason.TOOL_CALLS:
    messages.append(AssistantMessage(tool_calls=response.choices[0].message.tool_calls))
    
    tool_call = response.choices[0].message.tool_calls[0]
    func_args = json.loads(tool_call.function.arguments)
    
    print(f"Calling: {tool_call.function.name}({func_args})")
    func_response = get_weather(**func_args)
    
    messages.append(ToolMessage(func_response, tool_call_id=tool_call.id))
    
    final_response = client.complete(messages=messages, tools=[weather_tool])
    print(f"Model response: {final_response.choices[0].message.content}")

client.close()
```

### 8.4 Streaming + Tool Calling (azure-ai-inference)
The key difference is collecting streamed tool call fragments before calling the function:
```python
response = client.complete(messages=messages, tools=[weather_tool], stream=True)

tool_call_id = ""
function_name = ""
function_args = ""

for update in response:
    if update.choices[0].delta.tool_calls is not None:
        tc = update.choices[0].delta.tool_calls[0]
        if tc.function.name is not None:
            function_name = tc.function.name
        if tc.id is not None:
            tool_call_id = tc.id
        function_args += tc.function.arguments or ""

# After streaming completes, execute the tool call and follow up
messages.append(AssistantMessage(
    tool_calls=[ChatCompletionsToolCall(
        id=tool_call_id,
        function=FunctionCall(name=function_name, arguments=function_args)
    )]
))
# ... call function, append ToolMessage, call complete() again
```

### 8.5 Entra ID Auth (DefaultAzureCredential) for Managed Compute
```python
from azure.ai.inference import ChatCompletionsClient
from azure.identity import DefaultAzureCredential

client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=DefaultAzureCredential(exclude_interactive_browser_credential=False),
)
```

### 8.6 Azure OpenAI Endpoint (azure-ai-inference)
```python
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

# Note the specific URL format: includes /openai/deployments/<deployment-name>
client = ChatCompletionsClient(
    endpoint="https://<resource>.openai.azure.com/openai/deployments/<deployment-name>",
    credential=AzureKeyCredential(key),
    api_version="2024-06-01",  # Required for Azure OpenAI
)
```

### 8.7 Using azure-ai-projects 2.x with DefaultAzureCredential (New Foundry)
```python
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Run `az login` in terminal first for local dev
with (
    DefaultAzureCredential() as credential,
    AIProjectClient(
        endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        credential=credential
    ) as project_client,
):
    with project_client.get_openai_client() as openai_client:
        response = openai_client.responses.create(
            model=os.environ["FOUNDRY_MODEL_NAME"],
            input="Summarize the key benefits of exercise.",
        )
        print(response.output_text)
```

### 8.8 Async Client (azure-ai-inference)
```python
import asyncio
from azure.ai.inference.aio import ChatCompletionsClient
from azure.ai.inference.models import UserMessage
from azure.core.credentials import AzureKeyCredential

async def main():
    client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    response = await client.complete(messages=[UserMessage("Hello!")])
    print(response.choices[0].message.content)
    await client.close()

asyncio.run(main())
```

---

## 9. Package Versions and Install Commands

### Current Stable/Latest Versions (as of May 2026)

| Package | Latest Version | Released | Status |
|---|---|---|---|
| `azure-ai-inference` | 1.0.0b9 | Feb 14, 2025 | Beta (pre-release) |
| `azure-ai-projects` | 2.1.0 | Apr 20, 2026 | Stable |
| `azure-identity` | (latest) | — | Stable |
| `openai` | (latest) | — | Stable (required by azure-ai-projects 2.x) |

### Install Commands
```bash
# Core inference SDK (direct model calls)
pip install azure-ai-inference

# With OpenTelemetry tracing support
pip install azure-ai-inference[opentelemetry]

# Foundry project SDK (agents, evaluations, full project integration)
pip install azure-ai-projects>=2.0.0

# Authentication
pip install azure-identity

# Async support
pip install aiohttp

# OpenAI SDK (needed when using azure-ai-projects)
pip install openai

# Tracing / observability
pip install opentelemetry-sdk azure-core-tracing-opentelemetry azure-monitor-opentelemetry

# Recommended minimal set for azure-ai-inference local dev
pip install azure-ai-inference azure-identity

# Recommended minimal set for azure-ai-projects (Foundry) local dev
pip install "azure-ai-projects>=2.0.0" azure-identity
```

---

## 10. Gotchas and Important Notes

### 10.1 The Naming Rebranding is Confusing
- "Azure AI Studio" → "Azure AI Foundry" → "Microsoft Foundry" — all refer to the same evolving platform.
- Documentation URLs now use `/azure/foundry/` (new) and `/azure/foundry-classic/` (old hub-based).
- `azure-ai-projects` 2.x (new) is **NOT compatible** with 1.x. The endpoint format changed from connection strings (hub-based) to `https://<resource>.ai.azure.com/api/projects/<project>`.

### 10.2 azure-ai-inference is Still Beta
- `azure-ai-inference` 1.0.0b9 is the latest as of Feb 2025. It uses REST API version `2024-05-01-preview`.
- Despite being beta, it is actively used and stable enough for production by many teams.
- Microsoft themselves recommend using the official `openai` Python SDK for production Azure OpenAI scenarios.

### 10.3 Serverless API Endpoints Do NOT Support Entra ID
- Serverless endpoints only support API key authentication.
- Managed Compute endpoints support both API key and Entra ID.
- Azure OpenAI endpoints (standard deployments) support both.

### 10.4 Azure OpenAI Endpoint Requires `api_version`
When using `ChatCompletionsClient` against an Azure OpenAI endpoint, you **must** specify `api_version`. The latest stable version was `"2024-06-01"` at time of `azure-ai-inference` 1.0.0b9 release.

### 10.5 Managed Compute Endpoint Header
Some Managed Compute endpoints require the HTTP header `azureml-model-deployment` set to the deployment name. Pass it as:
```python
client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key),
    headers={"azureml-model-deployment": "your-deployment-name"},
)
```
Set `AZURE_AI_CHAT_DEPLOYMENT_NAME` env var in samples to trigger this.

### 10.6 model_extras for Model-Specific Parameters
Some models require extra parameters not in the standard spec. Use `model_extras`:
```python
response = client.complete(
    messages=[...],
    model_extras={"safe_mode": True},  # example for Mistral
)
```
This automatically adds the `extra-parameters: pass-through` HTTP header so the service doesn't reject the unknown field.

### 10.7 azure-ai-projects 2.x — Entra ID Only
The `AIProjectClient` (2.x) does NOT support API key auth. You must use `DefaultAzureCredential` or another TokenCredential. For local dev, run `az login` first.

### 10.8 load_client Limitation
The `load_client()` utility only works for Serverless API and Managed Compute endpoints. It does **not** work for GitHub Models or Azure OpenAI endpoints.

### 10.9 MOE LLM Compatibility Note
Mixture-of-Experts (MOE) LLM deployments may have compatibility issues with some features. The samples README notes this as a caveat.

### 10.10 Classic Hub Projects are in Maintenance Mode
Hub-based projects (Foundry classic) are still supported but new investments are focused on the new Foundry resource model. The `azure-ai-projects` 1.x which used hub-based connection strings (`<project>;<region>;<subscription>`) is effectively deprecated for new projects; use `azure-ai-projects` 2.x with the new endpoint format.

### 10.11 Tracing Requires Experimental Opt-In
GenAI tracing in `azure-ai-projects` 2.x requires:
```bash
export AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true
```
Must be set **before** calling `AIProjectInstrumentor().instrument()`.

### 10.12 Endpoint URL Formats Summary

| Deployment Type | Endpoint URL Format |
|---|---|
| Serverless API / Managed Compute | `https://<host-name>.<region>.models.ai.azure.com` |
| Azure OpenAI (via azure-ai-inference) | `https://<resource>.openai.azure.com/openai/deployments/<deployment>` |
| Foundry Project (via azure-ai-projects) | `https://<resource>.ai.azure.com/api/projects/<project>` |
| GitHub Models | `https://models.inference.ai.azure.com` |

---

## References

- [What is Microsoft Foundry (overview)](https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry)
- [Microsoft Foundry Quickstart (code)](https://learn.microsoft.com/en-us/azure/foundry/quickstarts/get-started-code)
- [Deployment Overview for Foundry Models (classic)](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/deployments-overview)
- [azure-ai-inference on PyPI](https://pypi.org/project/azure-ai-inference/)
- [azure-ai-projects on PyPI](https://pypi.org/project/azure-ai-projects/)
- [azure-ai-inference samples on GitHub](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/ai/azure-ai-inference/samples)
- [azure-ai-inference README](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-inference/README.md)
- [azure-ai-projects samples](https://aka.ms/azsdk/azure-ai-projects-v2/python/samples/)
