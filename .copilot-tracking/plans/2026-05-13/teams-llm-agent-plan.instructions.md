---
applyTo: '.copilot-tracking/changes/2026-05-13/teams-llm-agent-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: Teams LLM Agent with Azure AI Foundry

## Overview

Build a locally-running Python agent that uses an Azure AI Foundry-deployed LLM (via LangChain) and
can read and post messages to Microsoft Teams channels using the Microsoft Graph API.

## Objectives

### User Requirements

* Build a locally-running LLM agent that calls an Azure AI Foundry-deployed model — Source: User conversation
* Enable the agent to read messages from Microsoft Teams — Source: User conversation
* Enable the agent to write/post messages to Microsoft Teams — Source: User conversation
* Orchestrate agent behavior with tool use (Teams read/write as tools) — Source: User conversation

### Derived Objectives

* Use LangChain + langchain-azure-ai as the agent framework — Derived from: Research comparison of agent frameworks; best balance of Foundry connectivity, tooling ecosystem, and local-first simplicity. See `.copilot-tracking/research/subagents/2026-05-13/agent-frameworks-research.md`
* Use Microsoft Graph SDK for Teams access (not Bot Framework) — Derived from: Graph API requires no public endpoint for local dev, sufficient for read/write. Research: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Teams Bot Framework vs. Graph API)
* Use DeviceCodeCredential for Graph auth and DefaultAzureCredential for Foundry — Derived from: App-only credentials cannot post to Teams channels; delegated auth required. Research: `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` (Critical Teams Permission Constraint)
* Implement singleton GraphServiceClient in auth.py — Derived from: Prevents duplicate device-code prompts when both tool modules import the Graph client at module load. See DD-01 in planning log.
* Read deployment settings from .env — Derived from: Avoid hardcoded model names for flexibility across Foundry deployments. See DD-02 in planning log.

## Context Summary

### Project Files

* `/Users/alimurad/Desktop/projects/teams-agent/` — workspace root; no source files yet (new project)

### References

* `.copilot-tracking/research/2026-05-13/teams-llm-agent-research.md` — primary research: Foundry SDK, Graph API, framework evaluation, auth constraints, code samples
* `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` — implementation details (all file content)

### Standards References

* No repository-specific instruction files found in workspace

## Implementation Checklist

### [x] Implementation Phase 1: Project Scaffolding

<!-- parallelizable: true -->

* [x] Step 1.1: Create `requirements.txt` with all package dependencies
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 15-51)
* [x] Step 1.2: Create `.env.template` with all required environment variable placeholders
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 52-91)
* [x] Step 1.3: Create `tools/__init__.py` as an empty Python package marker
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 92-107)
* [x] Step 1.4: Create `.gitignore` to exclude `.env` and Python artifacts from version control
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 108-141)
* [x] Step 1.5: Validate phase — install packages and run quick import smoke test
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 142-149)

### [x] Implementation Phase 2: Authentication Module

<!-- parallelizable: false -->

* [x] Step 2.1: Create `auth.py` with `get_foundry_credential()` and singleton `get_graph_client()`
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 154-224)
* [x] Step 2.2: Validate phase — confirm `auth.py` imports cleanly
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 225-232)

### [x] Implementation Phase 3: Teams Tools

<!-- parallelizable: true -->

* [x] Step 3.1: Create `tools/teams_read.py` with `read_channel_messages` LangChain tool
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 237-296)
* [x] Step 3.2: Create `tools/teams_write.py` with `post_channel_message` LangChain tool
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 297-354)

### [x] Implementation Phase 4: Main Agent

<!-- parallelizable: false -->

* [x] Step 4.1: Create `agent.py` with LangChain AgentExecutor and interactive REPL loop
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 359-435)

### [x] Implementation Phase 5: Documentation

<!-- parallelizable: true -->

* [x] Step 5.1: Create `README.md` covering prerequisites, app registration, env config, and usage
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 440-476)

### [x] Implementation Phase 6: Validation

<!-- parallelizable: false -->

* [x] Step 6.1: Run full project validation including `AzureAIOpenAIApiChatModel` class-name verification
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 481-500)
* [x] Step 6.2: Fix minor validation issues including class-name correction if needed (see DR-06 in log)
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 501-511)
* [ ] Step 6.3: Report any blocking issues requiring additional research
  * Details: `.copilot-tracking/details/2026-05-13/teams-llm-agent-details.md` (Lines 512-520)

## Planning Log

See `.copilot-tracking/plans/logs/2026-05-13/teams-llm-agent-log.md` for discrepancy tracking,
implementation paths considered, and suggested follow-on work.

## Dependencies

* Python 3.11+
* Azure subscription with AI Foundry access and a deployed model (Standard or Serverless endpoint)
* Microsoft 365 / Teams tenant with an Entra app registration (see README for steps)
* `az login` completed on the local machine (for `DefaultAzureCredential`)
* Admin consent granted for `ChannelMessage.Read.All` in the app registration

## Success Criteria

* Agent authenticates with Azure AI Foundry and calls the LLM — Traces to: User requirement (LLM agent)
* Agent reads messages from a Teams channel using `read_channel_messages` — Traces to: User requirement (read Teams)
* Agent posts a message to a Teams channel using `post_channel_message` — Traces to: User requirement (write Teams)
* End-to-end execution works with `python agent.py` — Traces to: User requirement (locally running)
* Device code authentication triggers once per process, not twice — Traces to: Derived objective (singleton client)
* All modules import cleanly with no circular dependencies — Traces to: Derived objective (clean module structure)
