<!-- markdownlint-disable-file -->
# Release Changes: Teams LLM Agent with Azure AI Foundry

**Related Plan**: teams-llm-agent-plan.instructions.md
**Implementation Date**: 2026-05-13

## Summary

Build a locally-running Python agent that uses an Azure AI Foundry-deployed LLM (via LangChain) and
can read and post messages to Microsoft Teams channels using the Microsoft Graph API.

## Changes

### Added

* `requirements.txt` — Python package dependencies (Phase 1.1)
* `.env.template` — environment variable template with Azure Foundry and Teams placeholders (Phase 1.2)
* `tools/__init__.py` — empty package marker for tools directory (Phase 1.3)
* `.gitignore` — excludes `.env` and Python artifacts from version control (Phase 1.4)
* `auth.py` — credential factories: `get_foundry_credential()` (DefaultAzureCredential) and singleton `get_graph_client()` (DeviceCodeCredential) (Phase 2.1)
* `tools/teams_read.py` — `read_channel_messages` LangChain `@tool` to read recent messages from a Teams channel (Phase 3.1)
* `tools/teams_write.py` — `post_channel_message` LangChain `@tool` to post plain-text messages to a Teams channel (Phase 3.2)
* `agent.py` — main agent entry point with `AzureAIChatCompletionsModel` LLM, Teams tools, and interactive REPL loop (Phase 4.1)
* `README.md` — project documentation covering prerequisites, app registration, env config, installation, and usage (Phase 5.1)

### Modified

<!-- Populated as phases complete -->

### Removed

<!-- Populated as phases complete -->

## Additional or Deviating Changes

* `pip` not on system PATH — validation uses `python3 -m pip`; README instructions should reference `python3 -m pip install -r requirements.txt` instead of bare `pip install`.
  * Reason: macOS system configuration; not a code deviation.
* `auth.py` — added `from __future__ import annotations` for Python 3.9 compatibility.
  * Reason: System Python is 3.9; `GraphServiceClient | None` union syntax requires Python 3.10+. `from __future__ import annotations` defers annotation evaluation, preserving identical runtime behavior.
* `agent.py` — class name changed from `AzureAIOpenAIApiChatModel` to `AzureAIChatCompletionsModel` (import from `langchain_azure_ai.chat_models.inference`).
  * Reason: DR-06 confirmed: `AzureAIOpenAIApiChatModel` does not exist in the installed `langchain-azure-ai` package. Class discovery revealed `AzureAIChatCompletionsModel` as the correct name.
* `agent.py` — added `credential=DefaultAzureCredential()` parameter and renamed `deployment_name` → `model_name`.
  * Reason: `AzureAIChatCompletionsModel` requires an explicit `credential` argument; `model_name` is the correct field name per the class schema.

## Release Summary

**Total phases completed:** 6 of 6  
**Files created:** 8  
**Files modified:** 0  
**Files removed:** 0  
**Validation status:** Passed (all 9 checks)

### Files Created

| File | Purpose |
|------|---------|
| `requirements.txt` | Python package dependencies (Azure Identity, LangChain, langchain-azure-ai, msgraph-sdk, python-dotenv) |
| `.env.template` | Environment variable template with Azure Foundry and Teams placeholders |
| `.gitignore` | Excludes `.env` and Python artifacts from version control (OWASP A02 baseline) |
| `tools/__init__.py` | Empty package marker for tools directory |
| `auth.py` | Credential factories: `DefaultAzureCredential` for Foundry, singleton `DeviceCodeCredential` Graph client |
| `tools/teams_read.py` | LangChain `@tool`: reads recent messages from a Teams channel via Graph API |
| `tools/teams_write.py` | LangChain `@tool`: posts plain-text messages to a Teams channel via Graph API |
| `agent.py` | Main entry point: `AzureAIChatCompletionsModel` LLM + Teams tools + interactive REPL loop |
| `README.md` | Full developer guide: prerequisites, app registration, env config, installation, usage, extending |

### Key Deviations

1. **DR-06 resolved**: `AzureAIOpenAIApiChatModel` does not exist; replaced with `AzureAIChatCompletionsModel` from `langchain_azure_ai.chat_models.inference`. Added `credential=DefaultAzureCredential()` and renamed `deployment_name` → `model_name`.
2. **Python 3.9 compat**: Added `from __future__ import annotations` to `auth.py` for `X | None` union syntax support on system Python 3.9.
3. **pip invocation**: Use `python3 -m pip install -r requirements.txt` (bare `pip` not on system PATH on this machine).

### Deployment Notes

* Requires `.env` populated from `.env.template` with real Azure Foundry and Teams credentials before running.
* Run `az login` before `python3 agent.py` to satisfy `DefaultAzureCredential` for Foundry authentication.
* Device code authentication (Teams) triggers once at startup via the singleton `GraphServiceClient` in `auth.py`.
* No cloud deployment required — runs fully locally.
