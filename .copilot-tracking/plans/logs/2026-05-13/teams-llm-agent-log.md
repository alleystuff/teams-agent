<!-- markdownlint-disable-file -->
# Planning Log: Teams LLM Agent with Azure AI Foundry

## Discrepancy Log

Gaps and differences identified between research findings and the implementation plan.

### Unaddressed Research Items

* DR-01: Delta query polling for new messages (`GET /chatmessage/delta`)
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Potential Follow-Up Research section)
  * Reason: Reactive agent pattern is out of scope for initial implementation; REPL pull model is sufficient
  * Impact: low

* DR-02: Resource-Specific Consent (RSC) for `ChannelMessage.Read.Group`
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Potential Follow-Up Research section)
  * Reason: RSC reduces admin consent scope but adds app manifest complexity; deferring for initial build
  * Impact: low

* DR-03: Token caching for DeviceCodeCredential (avoid re-auth on every run)
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Potential Follow-Up Research section)
  * Reason: Dev convenience improvement; acceptable to re-authenticate per-run for initial build
  * Impact: low

* DR-04: Adaptive cards posting via Graph API
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Potential Follow-Up Research section)
  * Reason: Plain-text messaging satisfies the initial scope; card formatting is an enhancement
  * Impact: low

* DR-05: `devtunnel` / `ngrok` for local webhook subscriptions (event-driven pattern)
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Potential Follow-Up Research section)
  * Reason: Requires a public endpoint; polling REPL is simpler for local dev
  * Impact: low

* DR-06: `AzureAIOpenAIApiChatModel` class name unverified against published `langchain-azure-ai` API reference
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Agent Framework Landscape table)
  * Reason: Research cites class name without a link to package API reference; naming does not match typical LangChain-Azure conventions; risk identified by Plan Validator
  * Impact: high — if class name is wrong, `agent.py` fails to import and all user requirements are blocked

* DR-07: No `.gitignore` to exclude `.env` from version control (security gap)
  * Source: OWASP A02 (Sensitive Data Exposure) baseline; identified by Plan Validator
  * Reason: Original research scaffolding did not include a `.gitignore`; `.env` holds live Azure and Teams credentials
  * Impact: high — accidental credential commit risk; addressed in plan as Step 1.4

### Plan Deviations from Research

* DD-01: Singleton `GraphServiceClient` in `auth.py`
  * Research recommends: Each tool module calls `get_graph_client()` which creates a new `GraphServiceClient` and `DeviceCodeCredential` per call
  * Plan implements: `auth.py` uses a `_graph_client` module-level variable so `get_graph_client()` returns the same instance on every call; device code flow triggers once per process
  * Rationale: Without the singleton, importing both `tools/teams_read.py` and `tools/teams_write.py` at startup would trigger two device code prompts, degrading the developer experience. The singleton is backward-compatible: callers still use `get_graph_client()` and the interface is identical.

* DD-02: Deployment name and API version read from environment variables
  * Research recommends: `deployment_name="gpt-4o"` hardcoded in `agent.py`
  * Plan implements: `deployment_name=os.environ.get("AZURE_AI_DEPLOYMENT", "gpt-4o")` and `api_version=os.environ.get("AZURE_AI_API_VERSION", "2024-06-01")` with `.env` defaults
  * Rationale: Allows switching between Foundry deployments without code changes; defaults preserve research behavior when env vars are absent.

* DD-03: `load_dotenv()` called before tool module imports in `agent.py`
  * Research recommends: `load_dotenv()` called after all imports (as shown in Scenario A `agent.py` sample)
  * Plan implements: `load_dotenv()` called immediately after the standard-library imports, before any project-level imports
  * Rationale: Tool modules (`tools/teams_read.py`, `tools/teams_write.py`) execute `graph = get_graph_client()` at module load time, which reads `os.environ["TEAMS_CLIENT_ID"]` via a bare key lookup. If `load_dotenv()` is called after those imports, the `.env` values are never available when the key lookup runs, causing `KeyError: TEAMS_CLIENT_ID`. The research sample has the same ordering bug and must not be followed on this point.

* DD-04 (implementation-discovered): `AzureAIOpenAIApiChatModel` does not exist in installed `langchain-azure-ai`
  * Plan specifies: `AzureAIOpenAIApiChatModel` from `langchain_azure_ai` (DR-06 flagged as high-risk)
  * Implementation differs: `AzureAIChatCompletionsModel` from `langchain_azure_ai.chat_models.inference`
  * Rationale: Class discovery at Phase 4 confirmed `AzureAIOpenAIApiChatModel` is absent; `AzureAIChatCompletionsModel` is the correct class in the installed package version.

* DD-05 (implementation-discovered): `AzureAIChatCompletionsModel` requires `credential` parameter and uses `model_name` not `deployment_name`
  * Plan specifies: `AzureAIOpenAIApiChatModel(endpoint=..., deployment_name=..., api_version=...)`
  * Implementation differs: `AzureAIChatCompletionsModel(endpoint=..., credential=DefaultAzureCredential(), model_name=..., api_version=...)`
  * Rationale: Actual class schema requires explicit `credential` argument; field is `model_name`, not `deployment_name`.

* DD-06 (implementation-discovered): `from __future__ import annotations` added to `auth.py`
  * Plan specifies: `_graph_client: GraphServiceClient | None = None` (Python 3.10+ union syntax)
  * Implementation differs: `from __future__ import annotations` prepended to defer annotation evaluation
  * Rationale: System Python is 3.9; `X | None` syntax raises `TypeError` at runtime without the future import.

---

## Implementation Paths Considered

### Selected: LangChain + langchain-azure-ai

* Approach: Use `AzureAIOpenAIApiChatModel` from `langchain-azure-ai` as the LLM provider; Teams read/write as `@tool`-decorated functions using the Microsoft Graph SDK; `create_tool_calling_agent` + `AgentExecutor` for orchestration.
* Rationale: Broadest tooling ecosystem, native Foundry connectivity, most examples available, lowest boilerplate for 2-tool agent.
* Evidence: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Agent Framework Landscape section, Scenario A)

### IP-01: Semantic Kernel / Microsoft Agent Framework 1.0

* Approach: `@kernel_function` plugins for Teams tools; `AzureChatCompletion` connector for Foundry; stable LTS from Microsoft
* Trade-offs: Better long-term fit for M365 Copilot publishing and A2A protocol; slightly more ceremony (`KernelPlugin` registration vs. `@tool` decorator); fewer community examples than LangChain
* Rejection rationale: LangChain delivers the same local functionality with less boilerplate for a 2-tool agent; Semantic Kernel is the recommended upgrade path if M365 Copilot publishing becomes a requirement

### IP-02: AutoGen 0.7.5

* Approach: `AzureAIChatCompletionClient` for non-OpenAI Foundry models (Phi-4, Llama, Mistral); async-first agent loop
* Trade-offs: Best fit for multi-agent orchestration or non-OpenAI model endpoints; async-first adds friction for a simple local REPL; release cadence slowed (last release Sep 2025)
* Rejection rationale: Unnecessary complexity for a 2-tool, single-agent local script; async-first requires more boilerplate at the REPL layer

### IP-03: Azure AI Foundry Agent Service

* Approach: Fully managed cloud agent service with YAML/container tool definitions; hosted orchestration
* Trade-offs: Zero local infrastructure management; rich observability via Foundry portal; cannot run locally without wrapping as cloud sub-agents
* Rejection rationale: Does not satisfy the "runs locally" user requirement

### IP-04: Custom Loop (no framework)

* Approach: Direct `openai` SDK calls with manual JSON tool dispatch and multi-turn conversation state
* Trade-offs: Zero framework dependencies; maximum control; requires hand-coding tool dispatch, error handling, and conversation history
* Rejection rationale: Not worth the duplication for a project with 2+ tools; framework overhead is justified

### IP-05: Teams Bot Framework (vs. Graph API)

* Approach: Azure Bot Service registration, Bot Framework SDK, proactive messaging, rich adaptive card UX
* Trade-offs: Richer Teams UX; requires a public HTTPS endpoint (ngrok/devtunnel for local dev); complex registration; larger dependency surface
* Rejection rationale: Graph API is sufficient for read/write messages with no public endpoint requirement; simpler auth and setup for local dev

---

## Suggested Follow-On Work

Items identified during planning that fall outside current scope.

* WI-01: Delta query polling for reactive agent — implement `GET /teams/{id}/channels/{id}/messages/delta` to let the agent react to new messages without a webhook (medium priority)
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Potential Follow-Up Research)
  * Dependency: Initial agent implementation complete

* WI-02: DeviceCodeCredential token caching — persist MSAL token cache to disk so the agent does not re-authenticate on every run (medium priority)
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Potential Follow-Up Research)
  * Dependency: Initial agent implementation complete

* WI-03: Resource-Specific Consent (RSC) — replace tenant-wide `ChannelMessage.Read.All` admin consent with per-team `ChannelMessage.Read.Group` RSC to reduce blast radius (low priority)
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Potential Follow-Up Research)
  * Dependency: Initial agent implementation complete; requires Teams app manifest

* WI-04: Additional tools — `list_teams`, `list_channels`, `reply_to_thread`, `react_to_message` (low priority)
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Extending section)
  * Dependency: Initial tools framework established

* WI-05: Adaptive cards posting — extend `post_channel_message` to accept card JSON and post with `contentType: "html"` or an attachment (low priority)
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Potential Follow-Up Research)
  * Dependency: Initial agent implementation complete

* WI-06: Upgrade to Semantic Kernel / MAF — migrate from LangChain to Semantic Kernel if M365 Copilot publishing or multi-agent A2A orchestration becomes a requirement (medium priority)
  * Source: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Considered Alternatives — Semantic Kernel)
  * Dependency: WI-04 (more tools) motivates the migration; plan separately

* WI-07: Add `pytest` smoke-test suite with mocked credentials (low priority) — identified during Phase 6 validation
  * Source: Phase 6 subagent suggestion
  * Dependency: Initial agent implementation complete

* WI-08: Consider `python_requires >= "3.10"` in `pyproject.toml` to surface Python version requirement early — identified during Phase 2
  * Source: Phase 2 subagent suggestion
  * Dependency: None
