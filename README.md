---
title: Teams LLM Agent
description: A locally-running Python agent that reads and posts Microsoft Teams messages using Azure AI Foundry and the Microsoft Graph API.
author: teams-agent
ms.date: 2026-05-13
ms.topic: overview
keywords:
  - azure-ai-foundry
  - langchain
  - microsoft-teams
  - microsoft-graph
  - python-agent
---

## Overview

Teams LLM Agent is a locally-running Python application that connects an Azure AI Foundry language model to Microsoft Teams. It uses LangChain's tool-calling agent pattern with `AzureAIChatCompletionsModel` (from `langchain_azure_ai.chat_models.inference`) as the LLM, and the Microsoft Graph SDK to read channel messages and post replies. Authentication for Azure AI Foundry uses `DefaultAzureCredential` (satisfied by `az login`), while Graph API access uses the device code flow so the agent acts on behalf of a signed-in user without requiring a client secret.

## Prerequisites

Before you begin, make sure you have:

- Python 3.10 or later (the project includes `from __future__ import annotations` for syntax compatibility, but Python 3.10+ is recommended to avoid runtime issues)
- An Azure subscription with an Azure AI Foundry resource and a deployed model (for example, `gpt-4o`)
- A Microsoft 365 tenant with Microsoft Teams
- Azure CLI installed and signed in (`az login`)

## Installation

1. Clone or copy this repository to your local machine.

2. Install the required Python packages:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

## App Registration

The agent uses delegated Graph API permissions, which require an Entra app registration configured for the device code flow.

1. Go to the [Entra admin center](https://entra.microsoft.com) and select **App registrations**, then **New registration**.
2. Set the name to `Teams LLM Agent (local dev)` and select **Single tenant**.
3. Under **Redirect URI**, choose platform **Mobile and desktop** and set the URI to `http://localhost`.
4. Select **Register** to create the registration.
5. Go to **Authentication** and under **Advanced settings**, set **Allow public client flows** to **Yes**. This setting is required for the device code flow.
6. Go to **API permissions**, select **Add a permission**, then select **Microsoft Graph** and **Delegated permissions**. Add the following:
   - `Team.ReadBasic.All`
   - `Channel.ReadBasic.All`
   - `ChannelMessage.Read.All`
   - `ChannelMessage.Send`
7. Select **Grant admin consent** for `ChannelMessage.Read.All` (this permission requires admin consent in most tenants).
8. On the **Overview** page, copy the **Application (client) ID** value. You will use this as `TEAMS_CLIENT_ID`.
9. On the **Overview** page, copy the **Directory (tenant) ID** value. You will use this as `TEAMS_TENANT_ID`.

## Environment Configuration

1. Copy the template to `.env`:

   ```bash
   cp .env.template .env
   ```

2. Open `.env` and fill in each value:

   ```dotenv
   AZURE_AI_ENDPOINT=https://<your-foundry-resource>.openai.azure.com/
   AZURE_AI_DEPLOYMENT=gpt-4o
   AZURE_AI_API_VERSION=2024-06-01
   TEAMS_CLIENT_ID=<application-client-id>
   TEAMS_TENANT_ID=<directory-tenant-id>
   ```

Variable reference:

| Variable | Description |
|---|---|
| `AZURE_AI_ENDPOINT` | The endpoint URL for your Azure AI Foundry resource (standard deployment). Must end with `/`. |
| `AZURE_AI_DEPLOYMENT` | The name of your deployed model, for example `gpt-4o` or `gpt-4.1`. |
| `AZURE_AI_API_VERSION` | The Azure OpenAI API version to use, for example `2024-06-01`. |
| `TEAMS_CLIENT_ID` | The Application (client) ID from your Entra app registration. |
| `TEAMS_TENANT_ID` | The Directory (tenant) ID from your Entra app registration. |

> [!NOTE]
> `DefaultAzureCredential` authenticates to Azure AI Foundry using your active `az login` session. Run `az login` before starting the agent if your session has expired.

## Running

Start the agent:

```bash
python3 agent.py
```

On the first run, the agent prints a device code prompt similar to:

```
To sign in, use a web browser to open the page https://microsoft.com/devicelogin
and enter the code XXXXXXXXX to authenticate.
```

Open the URL in your browser, enter the code, and sign in with a Microsoft 365 account that has access to the Teams channels you want to use. After authentication, the agent enters an interactive REPL:

```
You: what are the latest messages in channel <channel-id> of team <team-id>?
```

You can ask the agent to read messages or post to any channel your account can access. To exit, type `exit` or `quit`.

## Project Structure

```
teams-agent/
├── .env                   # Runtime configuration (not committed)
├── .env.template          # Template — copy to .env and fill in values
├── .gitignore
├── requirements.txt       # Python dependencies
├── agent.py               # Entry point: assembles the LangChain agent and runs the REPL
├── auth.py                # Credential factories for Foundry (DefaultAzureCredential) and Graph (DeviceCodeCredential)
└── tools/
    ├── __init__.py
    ├── teams_read.py      # Tool: read_channel_messages
    └── teams_write.py     # Tool: post_channel_message
```

## Extending

To add more Graph capabilities, follow the pattern used in `tools/teams_read.py` and `tools/teams_write.py`:

1. Create a new file in `tools/` and decorate a function with `@tool`.
2. Import `get_graph_client` from `auth` to get an authenticated Graph client.
3. Add the new tool to the `tools` list in `agent.py`.

Useful tools to consider adding:

- `list_teams`: call `graph.me.joined_teams.get()` to return the teams the signed-in user belongs to.
- `list_channels`: call `graph.teams.by_team_id(team_id).channels.get()` to list channels for a given team.

For a production deployment or to publish the agent as a Microsoft 365 Copilot plugin, consider migrating to [Semantic Kernel](https://learn.microsoft.com/semantic-kernel/overview/), which provides native support for M365 Copilot publishing and declarative agent manifests.
# teams-agent
