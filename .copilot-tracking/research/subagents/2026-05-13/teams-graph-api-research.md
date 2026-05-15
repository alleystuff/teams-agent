# Research: Reading and Writing Microsoft Teams Messages via Microsoft Graph API (Python, Local Dev)

**Date:** 2026-05-13  
**Status:** Complete  
**Sources:** Microsoft Learn docs, GitHub microsoftgraph/msgraph-sdk-python

---

## Table of Contents

1. [Graph API Endpoints for Teams Messaging](#1-graph-api-endpoints)
2. [Authentication and Permissions](#2-authentication-and-permissions)
3. [Python SDK Options and Code Examples](#3-python-sdk-options)
4. [App Registration Steps](#4-app-registration-steps)
5. [Teams Bot Framework vs Graph API Direct](#5-bot-framework-vs-graph-api)
6. [Rate Limits and Throttling](#6-rate-limits-and-throttling)
7. [Known Limitations](#7-known-limitations)
8. [Quick-Start Checklist](#8-quick-start-checklist)

---

## 1. Graph API Endpoints

Base URL: `https://graph.microsoft.com/v1.0`

### 1.1 Teams / Channels

| Action | HTTP | Path |
|---|---|---|
| List teams the signed-in user belongs to | GET | `/me/joinedTeams` |
| Get a specific team | GET | `/teams/{team-id}` |
| List channels in a team | GET | `/teams/{team-id}/channels` |
| Get a specific channel | GET | `/teams/{team-id}/channels/{channel-id}` |

### 1.2 Channel Messages

| Action | HTTP | Path |
|---|---|---|
| List channel messages (no replies) | GET | `/teams/{team-id}/channels/{channel-id}/messages` |
| Get a single channel message | GET | `/teams/{team-id}/channels/{channel-id}/messages/{message-id}` |
| List replies to a message | GET | `/teams/{team-id}/channels/{channel-id}/messages/{message-id}/replies` |
| Post to channel | POST | `/teams/{team-id}/channels/{channel-id}/messages` |
| Post a reply | POST | `/teams/{team-id}/channels/{channel-id}/messages/{message-id}/replies` |
| Get all messages across all channels in a team | GET | `/teams/{team-id}/channels/getAllMessages` |

**OData query params supported for list:**
- `$top` — max 50 per page (default 20)
- `$expand=replies` — includes up to 200 replies per message
- `@odata.nextLink` in response — use for pagination

### 1.3 Chats (1:1 and Group DMs)

| Action | HTTP | Path |
|---|---|---|
| List chats for signed-in user | GET | `/me/chats` |
| Get a specific chat | GET | `/chats/{chat-id}` |
| List messages in a chat | GET | `/chats/{chat-id}/messages` |
| List messages (alternate paths) | GET | `/me/chats/{chat-id}/messages` |
| List messages (alternate paths) | GET | `/users/{user-id}/chats/{chat-id}/messages` |
| Post a message to a chat | POST | `/chats/{chat-id}/messages` |
| Get all chat messages for a user | GET | `/users/{user-id}/chats/getAllMessages` |

**Notes for chat list:**
- `$top` max 50
- `$orderby` supports `lastModifiedDateTime` (default) and `createdDateTime` (descending only)
- `$filter` on `lastModifiedDateTime` and `createdDateTime` (must be used together with `$orderby` for same property)

### 1.4 Delta / Subscriptions (Real-Time Change Notifications)

For receiving new messages without polling, use webhook subscriptions (Graph Change Notifications).

| Scope | Resource to subscribe | App-only? |
|---|---|---|
| All channel messages across tenant | `/teams/getAllMessages` | Yes (ChannelMessage.Read.All) |
| All chat messages across tenant | `/chats/getAllMessages` | Yes (Chat.Read.All) |
| Specific channel | `/teams/{team-id}/channels/{channel-id}/messages` | Both |
| Specific chat | `/chats/{chat-id}/messages` | Both |
| All chats for a user | `/users/{user-id}/chats/getAllMessages` | Both |

**Subscribe request body:**
```json
POST /v1.0/subscriptions
{
  "changeType": "created,updated",
  "notificationUrl": "https://your-public-webhook.example.com/api/notifications",
  "resource": "/teams/{team-id}/channels/{channel-id}/messages",
  "includeResourceData": false,
  "expirationDateTime": "2026-05-14T11:00:00.0000000Z",
  "clientState": "your-secret-client-state"
}
```

**Important subscription constraints:**
- `notificationUrl` must be a publicly reachable HTTPS endpoint — **not suitable for raw localhost** without a tunnel (ngrok, devtunnel, Azure Relay)
- If `expirationDateTime` > 1 hour, a `lifecycleNotificationUrl` property is also required
- For local dev with subscriptions, use `microsoft/devtunnel` or `ngrok http 3978`

There is also a **delta query** for chat messages: `GET /chatmessage/delta` — allows polling for incremental changes with a delta token. Polling is restricted to once per day per resource unless using subscriptions.

---

## 2. Authentication and Permissions

### 2.1 Permission Scopes Table

| Operation | Delegated (least-priv) | Application (least-priv) | Notes |
|---|---|---|---|
| Read channel messages | `ChannelMessage.Read.All` | `ChannelMessage.Read.All` or `ChannelMessage.Read.Group`* | Admin consent required |
| Post to channel | `ChannelMessage.Send` | `Teamwork.Migrate.All` | **App-only posting only for migration; not for regular use** |
| Read chat messages | `Chat.Read` | `Chat.Read.All` or `ChatMessage.Read.Chat`* | Admin consent for app-only |
| Post to chat | `ChatMessage.Send` | `Teamwork.Migrate.All` | **App-only posting only for migration; not for regular use** |
| List joined teams | `Team.ReadBasic.All` | `Team.ReadBasic.All` | |
| List channels | `Channel.ReadBasic.All` | `Channel.ReadBasic.All` | |
| List/get chats | `Chat.ReadBasic` | `Chat.ReadBasic.All` | |
| Subscribe to channel messages | `ChannelMessage.Read.All` | `ChannelMessage.Read.All` | Admin consent |
| Subscribe to chat messages | `Chat.Read` | `Chat.Read.All` | Admin consent for app-only |

`*` = resource-specific consent (RSC) — scoped to individual team/chat

### 2.2 Auth Flow Recommendations for Local Dev

**For delegated (on behalf of a user):**

| Flow | Python Class | Best For |
|---|---|---|
| **Device Code** (recommended for local dev) | `DeviceCodeCredential` from `azure.identity` | CLI scripts, headless environments, no browser needed locally — user authenticates on another device |
| Interactive Browser | `InteractiveBrowserCredential` from `azure.identity` | Local dev with a browser available |
| Authorization Code | `AuthorizationCodeCredential` from `azure.identity.aio` | Web apps |
| Username/Password | `UsernamePasswordCredential` from `azure.identity` | Only when other flows not viable — NOT recommended |

**For app-only (without a user):**

| Flow | Python Class | Best For |
|---|---|---|
| Client Credentials (secret) | `ClientSecretCredential` from `azure.identity.aio` | Background services, daemon apps |
| Client Credentials (cert) | `CertificateCredential` from `azure.identity.aio` | Production services (more secure than secret) |

**Key decision for local dev agent:**
- If you need to **post messages** (to channel or chat), you **must use delegated permissions** because application permissions for posting are only supported in migration scenarios (`Teamwork.Migrate.All`)
- If you only need to **read messages**, you can use either delegated or application permissions
- **Device Code flow** is the easiest for local dev: the script prints a URL and code, you log in on any browser, the script gets the token automatically

### 2.3 Auth Flow (Device Code — Text Diagram)

```
Local Python Script                Microsoft Identity Platform
        |                                       |
        |-- POST /oauth2/v2.0/devicecode ------>|
        |<-- { device_code, user_code, url } ---|
        |                                       |
        | (prints: "Visit https://... and enter code XXXX-XXXX")
        |                                       |
        |-- Poll POST /oauth2/v2.0/token ------>|  (every 5s)
        |<-- { access_token } -----------------|  (after user logs in)
        |                                       |
        |-- GET /graph.microsoft.com/v1.0/... ->|  (with Bearer token)
        |<-- { data } --------------------------|
```

### 2.4 Auth Flow (Client Credentials — Text Diagram)

```
Local Python Script                Microsoft Identity Platform
        |                                       |
        |-- POST /oauth2/v2.0/token ----------->|
        |   (client_id + client_secret + scope) |
        |<-- { access_token } ------------------|
        |                                       |
        |-- GET /graph.microsoft.com/v1.0/... ->|  (with Bearer token)
        |<-- { data } --------------------------|
```

---

## 3. Python SDK Options

### 3.1 Package Options

| Package | PyPI | Purpose |
|---|---|---|
| `msgraph-sdk` | msgraph-sdk | **Recommended** — full Graph SDK with fluent API, models, request builders for v1.0 |
| `msgraph-beta-sdk` | msgraph-beta-sdk | Beta endpoint (same architecture) |
| `msgraph-core` | msgraph-core | Lower-level HTTP middleware without generated models |
| `azure-identity` | azure-identity | Authentication (MSAL-backed credential classes) |
| `requests` / `httpx` | built-in / httpx | Raw HTTP; you manage token acquisition yourself using `msal` |

**Install (recommended):**
```bash
pip install msgraph-sdk azure-identity
```

Note: `msgraph-sdk` is a large package; first install may take a few minutes. Enable long paths on Windows if needed.

Current version: **1.57.0** (as of May 2026). Updated bi-weekly (2nd and 4th week of each month).

### 3.2 `msgraph-sdk` vs `msgraph-core`

- `msgraph-sdk` = models + request builders (typed, fluent, generated from OpenAPI) + depends on `msgraph-core`
- `msgraph-core` = HTTP client middleware, retry, redirect, paging — no typed models
- For new code: **always use `msgraph-sdk`** unless you need to call an endpoint not yet in the generated SDK

### 3.3 Key Classes

| Class | Import | Role |
|---|---|---|
| `GraphServiceClient` | `from msgraph import GraphServiceClient` | Main entry point for all Graph calls |
| `DeviceCodeCredential` | `from azure.identity import DeviceCodeCredential` | Delegated auth via device code (sync) |
| `ClientSecretCredential` | `from azure.identity.aio import ClientSecretCredential` | App-only auth (async) |
| `ChatMessage` | `from msgraph.generated.models.chat_message import ChatMessage` | Message model for POST |
| `ItemBody` | `from msgraph.generated.models.item_body import ItemBody` | Message body |
| `MessagesRequestBuilder` | generated | Query parameter builder |
| `RequestConfiguration` | `from kiota_abstractions.base_request_configuration import RequestConfiguration` | Request-level config |
| `APIError` | `from kiota_abstractions.api_error import APIError` | Exception for failed requests |

### 3.4 Complete Code Example: Auth + List Channels + Read Messages + Post Message

```python
"""
teams_graph_example.py
Requires: pip install msgraph-sdk azure-identity

App registration:
  - Delegated permissions: ChannelMessage.Read.All, ChannelMessage.Send,
    Chat.Read, ChatMessage.Send, Team.ReadBasic.All, Channel.ReadBasic.All
  - Platform: Mobile and desktop (redirect: http://localhost)
  - Enable "Allow public client flows" = Yes
"""

import asyncio
import os

from azure.identity import DeviceCodeCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.chat_message import ChatMessage
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.teams.item.channels.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from kiota_abstractions.base_request_configuration import RequestConfiguration
from kiota_abstractions.api_error import APIError

# --- Configuration ---
CLIENT_ID = os.environ["AZURE_CLIENT_ID"]    # App registration client ID
TENANT_ID = os.environ["AZURE_TENANT_ID"]    # Your tenant ID or "common"

SCOPES = [
    "ChannelMessage.Read.All",
    "ChannelMessage.Send",
    "Chat.Read",
    "ChatMessage.Send",
    "Team.ReadBasic.All",
    "Channel.ReadBasic.All",
]

# --- Auth: Device Code Flow (best for local dev) ---
credential = DeviceCodeCredential(client_id=CLIENT_ID, tenant_id=TENANT_ID)
graph_client = GraphServiceClient(credentials=credential, scopes=SCOPES)


async def list_my_teams():
    """List all teams the signed-in user belongs to."""
    try:
        teams = await graph_client.me.joined_teams.get()
        if teams and teams.value:
            for team in teams.value:
                print(f"Team: {team.display_name}  ID: {team.id}")
        return teams
    except APIError as e:
        print(f"Error listing teams: {e.error.message}")


async def list_channels(team_id: str):
    """List all channels in a team."""
    try:
        channels = await graph_client.teams.by_team_id(team_id).channels.get()
        if channels and channels.value:
            for ch in channels.value:
                print(f"  Channel: {ch.display_name}  ID: {ch.id}")
        return channels
    except APIError as e:
        print(f"Error listing channels: {e.error.message}")


async def read_channel_messages(team_id: str, channel_id: str, top: int = 10):
    """Read the most recent messages from a channel."""
    try:
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            top=top,
        )
        request_configuration = RequestConfiguration(query_parameters=query_params)

        messages = await (
            graph_client
            .teams.by_team_id(team_id)
            .channels.by_channel_id(channel_id)
            .messages.get(request_configuration=request_configuration)
        )

        if messages and messages.value:
            for msg in messages.value:
                sender = msg.from_.user.display_name if msg.from_ and msg.from_.user else "System"
                content = msg.body.content if msg.body else ""
                print(f"  [{msg.created_date_time}] {sender}: {content[:100]}")

        # Handle pagination
        while messages and messages.odata_next_link:
            messages = await (
                graph_client
                .teams.by_team_id(team_id)
                .channels.by_channel_id(channel_id)
                .messages.with_url(messages.odata_next_link).get()
            )
            # process additional pages...

        return messages
    except APIError as e:
        print(f"Error reading messages: {e.error.message}")


async def post_channel_message(team_id: str, channel_id: str, text: str):
    """Post a plain-text message to a channel. Requires ChannelMessage.Send (delegated)."""
    try:
        request_body = ChatMessage(
            body=ItemBody(content=text),
        )
        result = await (
            graph_client
            .teams.by_team_id(team_id)
            .channels.by_channel_id(channel_id)
            .messages.post(request_body)
        )
        print(f"Posted message ID: {result.id}")
        return result
    except APIError as e:
        print(f"Error posting message: {e.error.message}")


async def list_my_chats():
    """List all chats (1:1 and group) the signed-in user is in."""
    try:
        chats = await graph_client.me.chats.get()
        if chats and chats.value:
            for chat in chats.value:
                print(f"Chat: {chat.chat_type}  ID: {chat.id}  Topic: {chat.topic}")
        return chats
    except APIError as e:
        print(f"Error listing chats: {e.error.message}")


async def read_chat_messages(chat_id: str, top: int = 10):
    """Read messages from a 1:1 or group chat."""
    try:
        from msgraph.generated.chats.item.messages.messages_request_builder import (
            MessagesRequestBuilder as ChatMessagesRequestBuilder,
        )
        query_params = ChatMessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            top=top,
        )
        request_configuration = RequestConfiguration(query_parameters=query_params)

        messages = await (
            graph_client
            .chats.by_chat_id(chat_id)
            .messages.get(request_configuration=request_configuration)
        )
        if messages and messages.value:
            for msg in messages.value:
                sender = msg.from_.user.display_name if msg.from_ and msg.from_.user else "System"
                content = msg.body.content if msg.body else ""
                print(f"  [{msg.created_date_time}] {sender}: {content[:100]}")
        return messages
    except APIError as e:
        print(f"Error reading chat messages: {e.error.message}")


async def post_chat_message(chat_id: str, text: str):
    """Post a message to a 1:1 or group chat. Requires ChatMessage.Send (delegated)."""
    try:
        request_body = ChatMessage(
            body=ItemBody(content=text),
        )
        result = await graph_client.chats.by_chat_id(chat_id).messages.post(request_body)
        print(f"Posted chat message ID: {result.id}")
        return result
    except APIError as e:
        print(f"Error posting chat message: {e.error.message}")


# --- Main ---
async def main():
    teams = await list_my_teams()
    if teams and teams.value:
        team_id = teams.value[0].id
        channels = await list_channels(team_id)
        if channels and channels.value:
            channel_id = channels.value[0].id
            await read_channel_messages(team_id, channel_id)
            await post_channel_message(team_id, channel_id, "Hello from Python!")

    chats = await list_my_chats()
    if chats and chats.value:
        chat_id = chats.value[0].id
        await read_chat_messages(chat_id)
        # await post_chat_message(chat_id, "Hello from Python!")


if __name__ == "__main__":
    asyncio.run(main())
```

### 3.5 App-Only (Client Credentials) — Read-Only Example

```python
"""
For reading messages without a signed-in user (background service).
NOTE: You cannot post messages with app-only credentials (only migration is allowed).
"""
import asyncio
from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient

credential = ClientSecretCredential(
    tenant_id="YOUR_TENANT_ID",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
)
scopes = ["https://graph.microsoft.com/.default"]
client = GraphServiceClient(credentials=credential, scopes=scopes)

async def read_all_channel_messages(team_id: str, channel_id: str):
    messages = await client.teams.by_team_id(team_id).channels.by_channel_id(channel_id).messages.get()
    for msg in (messages.value or []):
        print(msg.body.content)

asyncio.run(read_all_channel_messages("team-id", "channel-id"))
```

### 3.6 Using Raw `requests` (without SDK)

```python
"""
Manual approach using requests library with MSAL for token acquisition.
pip install requests msal
"""
import requests
import msal

CLIENT_ID = "YOUR_CLIENT_ID"
TENANT_ID = "YOUR_TENANT_ID"
SCOPES = ["https://graph.microsoft.com/ChannelMessage.Read.All",
          "https://graph.microsoft.com/ChannelMessage.Send"]

# Device Code Flow via MSAL directly
app = msal.PublicClientApplication(CLIENT_ID, authority=f"https://login.microsoftonline.com/{TENANT_ID}")
flow = app.initiate_device_flow(scopes=SCOPES)
print(flow["message"])  # e.g., "Go to https://microsoft.com/devicelogin and enter code XXXX-XXXX"
result = app.acquire_token_by_device_flow(flow)
access_token = result["access_token"]

headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
TEAM_ID = "your-team-id"
CHANNEL_ID = "your-channel-id"

# Read messages
resp = requests.get(
    f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/channels/{CHANNEL_ID}/messages",
    headers=headers
)
messages = resp.json()
for msg in messages.get("value", []):
    print(msg["body"]["content"])

# Post a message
resp = requests.post(
    f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/channels/{CHANNEL_ID}/messages",
    headers=headers,
    json={"body": {"content": "Hello from raw requests!"}}
)
print(resp.status_code, resp.json()["id"])
```

---

## 4. App Registration Steps

### 4.1 Register the App (Entra Admin Center)

1. Go to [Microsoft Entra admin center](https://entra.microsoft.com)
2. Navigate to **Identity > Applications > App registrations** > **New registration**
3. Enter a display name (e.g., `teams-python-agent`)
4. **Supported account types:**
   - Single org only: `Accounts in this organizational directory only`
   - Multi-tenant: `Accounts in any organizational directory`
5. Skip redirect URI for now, click **Register**
6. Copy the **Application (client) ID** and **Directory (tenant) ID** from the Overview page

### 4.2 For Delegated Flow (Device Code / Interactive)

1. Under **Manage > Authentication** > **Add a platform** > **Mobile and desktop applications**
2. Select `https://login.microsoftonline.com/common/oauth2/nativeclient` or add `http://localhost` as custom redirect URI
3. **CRITICAL:** Under **Advanced settings**, set **"Allow public client flows"** = **Yes** (required for Device Code flow)
4. Click **Save**

### 4.3 For App-Only Flow (Client Credentials)

1. Under **Manage > Certificates & secrets** > **Client secrets** > **New client secret**
2. Add a description and expiration (max 24 months)
3. **Copy the secret VALUE immediately** — it's never shown again
4. Store securely (environment variable, Azure Key Vault — never in code)

### 4.4 Grant API Permissions

1. Under **Manage > API permissions** > **Add a permission** > **Microsoft Graph**
2. **Delegated permissions** (for user-flow): add all needed scopes:
   - `ChannelMessage.Read.All`
   - `ChannelMessage.Send`
   - `Chat.Read`
   - `ChatMessage.Send`
   - `Team.ReadBasic.All`
   - `Channel.ReadBasic.All`
3. **Application permissions** (for app-only reading):
   - `ChannelMessage.Read.All`
   - `Chat.Read.All`
   - `Team.ReadBasic.All`
   - `Channel.ReadBasic.All`
4. Click **Grant admin consent for [your organization]** — required for most Teams permissions
5. Confirm the consent grant shows ✅ green checkmarks

### 4.5 .env File for Local Dev

```
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your-secret-value   # only for app-only flow
```

---

## 5. Bot Framework vs Graph API Direct

### 5.1 Comparison

| Aspect | Graph API Direct | Teams Bot Framework |
|---|---|---|
| **Setup complexity** | Low — just an app registration | High — Azure Bot registration, Bot channel configuration, manifest |
| **Local dev** | Easy — device code flow, no public URL needed for polling | Harder — requires public HTTPS webhook endpoint (ngrok/devtunnel) |
| **Posting messages** | Can post as signed-in user (delegated) | Posts as the bot identity (bot persona in Teams) |
| **Reading messages** | Poll or subscribe (webhook needed for subscriptions) | Receives messages via HTTP push to bot endpoint |
| **Real-time receive** | Subscriptions require public webhook URL | Native push — bot endpoint receives messages instantly |
| **Proactive messaging** | Possible via Graph, no Teams install needed | More complex, requires conversation reference |
| **Interactive UX** | None (text only via Graph) | Rich adaptive cards, task modules, dialogs |
| **Identity** | Appears as the user who auth'd (delegated) or as app | Appears as the bot (named persona) |
| **Cost** | Free (within API limits) | Free for local/dev; Azure Bot Service for production |
| **Best for** | Scripted automation, agents reading/posting on behalf of user | Interactive conversational bots with rich UX |

### 5.2 Recommendation for Local Dev Agent

**Use Graph API direct** if your agent:
- Reads messages for context / analysis
- Posts occasional messages on behalf of a user
- Runs as a CLI or background script
- Does not need real-time push (can poll with delta query)

**Use Bot Framework** if your agent:
- Needs real-time message receipt without polling
- Needs to appear as a named bot persona
- Needs adaptive cards, interactive dialogs
- Will eventually deploy to production in Teams

---

## 6. Rate Limits and Throttling

### 6.1 Teams-Specific Limits (requests per second)

| Operation | Per App | Per Tenant | Per Channel/Chat |
|---|---|---|---|
| GET channel message | 20 rps | 200 rps | 1 rps |
| GET 1:1/group chat message | 20 rps | 200 rps | 1 rps |
| POST channel message | 50 rps | 500 rps | 1 rps |
| POST 1:1/group chat message | 20 rps | 200 rps | 1 rps |
| GET team | 30 rps | 600 rps | — |
| GET channel | 30 rps | 600 rps | 1 rps |
| GET channels (list) | 60 rps | 1200 rps | 1 rps |
| POST channel | 30 rps | 300 rps | 1 rps |
| Get all channel messages (bulk) | 200 rps | 1000 rps | — |
| Get all chat messages (bulk) | 200 rps | 1000 rps | — |

**Additional hard limits:**
- Max **4 requests/second per app per team**
- Max **1 request/second per app per tenant** on a given **channel or chat**
- Max **1 request/second per user** for POST message in a given channel or chat
- Max **5 requests/second per user** for List/Get chats

### 6.2 Global Limit

- **130,000 requests per 10 seconds** across all services per tenant

### 6.3 Throttling Response

When throttled, the API returns `429 Too Many Requests`.  
Always check the `Retry-After` response header and back off accordingly.

```python
import asyncio
from kiota_abstractions.api_error import APIError

async def safe_get_messages(client, team_id, channel_id):
    for attempt in range(5):
        try:
            return await client.teams.by_team_id(team_id).channels.by_channel_id(channel_id).messages.get()
        except APIError as e:
            if e.response_status_code == 429:
                retry_after = int(e.response_headers.get("Retry-After", 10))
                await asyncio.sleep(retry_after)
            else:
                raise
```

### 6.4 Polling Requirements

- Do **not** poll resources more than **once per day** (except `teamsAsyncOperation`)
- For frequent updates: use **change notification subscriptions** (webhook)
- For moderate updates: use **delta query** with a delta token to get only incremental changes

---

## 7. Known Limitations

### 7.1 App-Only (Client Credentials) Cannot Post Messages

**This is the most critical limitation for agent development.**

- `POST /teams/{id}/channels/{id}/messages` — Application permissions: only `Teamwork.Migrate.All` (import messages only, not regular posting)
- `POST /chats/{id}/messages` — Application permissions: only `Teamwork.Migrate.All` (import messages only)
- **You cannot post regular messages as an app without a signed-in user.** This is by Microsoft design to prevent spam.
- Workaround: use delegated permissions (device code or interactive flow)

### 7.2 Reading Private/DM Chat Messages with App-Only

- **Possible** but requires `Chat.Read.All` application permission which requires **admin consent**
- Without admin consent, app-only cannot access private chats
- Delegated `Chat.Read` can only read chats the signed-in user is a member of

### 7.3 Reading Channel Messages Requires Admin Consent

- `ChannelMessage.Read.All` requires admin consent (both delegated and application)
- `ChannelMessage.Read.Group` (RSC) can work without tenant-wide admin consent but must be pre-authorized per-team

### 7.4 Subscriptions Require Public Webhook URL

- Webhook subscriptions need a publicly accessible HTTPS endpoint
- Not directly usable on localhost without a tunnel
- For local dev: use `ngrok http 3978` or Microsoft's `devtunnel` CLI
- Subscription max lifetime: typically **60 minutes** unless extended with renewal; `lifecycleNotificationUrl` is required for subscriptions > 1 hour

### 7.5 Polling Must Be Infrequent

- Polling the same resource more than once per day is a ToU violation
- Use delta queries or subscriptions for more frequent change detection
- Violation may result in throttling or API suspension

### 7.6 Message Body HTML Stripping

- Messages posted with `contentType: "text"` are plain text
- Messages with `contentType: "html"` support limited HTML (Teams subset only)
- Rich content (adaptive cards, file attachments) requires additional properties and possibly Bot Framework

### 7.7 Federation / Cross-Tenant

- When reading channels in application context, the request must be made from the tenant that owns the channel (tenant federation applies)

### 7.8 Personal Microsoft Accounts Not Supported

- Teams Graph API endpoints do not support personal Microsoft accounts (Xbox, Outlook.com, etc.)
- Only work/school accounts (Azure AD / Microsoft Entra ID)

---

## 8. Quick-Start Checklist

```
[ ] 1. Register app in Entra admin center (entra.microsoft.com)
[ ] 2. Copy Client ID and Tenant ID
[ ] 3. Add Mobile/Desktop platform, set redirect URI to http://localhost
[ ] 4. Enable "Allow public client flows" = Yes (for device code)
[ ] 5. Add delegated permissions:
        ChannelMessage.Read.All, ChannelMessage.Send,
        Chat.Read, ChatMessage.Send, Team.ReadBasic.All, Channel.ReadBasic.All
[ ] 6. Grant admin consent (requires org admin)
[ ] 7. pip install msgraph-sdk azure-identity
[ ] 8. Set environment variables: AZURE_CLIENT_ID, AZURE_TENANT_ID
[ ] 9. Run script — first run triggers device code prompt
[ ] 10. Authenticate via browser, token is cached for subsequent runs
```

---

## References

- [Microsoft Graph Teams API overview](https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview)
- [Microsoft Graph auth overview](https://learn.microsoft.com/en-us/graph/auth/)
- [Authentication and authorization basics](https://learn.microsoft.com/en-us/graph/auth/auth-concepts)
- [Choose an authentication provider (Python)](https://learn.microsoft.com/en-us/graph/sdks/choose-authentication-providers?tabs=python)
- [Install Microsoft Graph SDK](https://learn.microsoft.com/en-us/graph/sdks/sdk-installation)
- [Create a Graph client (Python)](https://learn.microsoft.com/en-us/graph/sdks/create-client?tabs=python)
- [List channel messages API](https://learn.microsoft.com/en-us/graph/api/channel-list-messages?view=graph-rest-1.0&tabs=python)
- [Post channel message API](https://learn.microsoft.com/en-us/graph/api/channel-post-messages?view=graph-rest-1.0&tabs=python)
- [List chat messages API](https://learn.microsoft.com/en-us/graph/api/chat-list-messages?view=graph-rest-1.0&tabs=python)
- [Post chat message API](https://learn.microsoft.com/en-us/graph/api/chat-post-messages?view=graph-rest-1.0&tabs=python)
- [Change notifications for Teams messages](https://learn.microsoft.com/en-us/graph/teams-changenotifications-chatmessage)
- [Graph throttling limits](https://learn.microsoft.com/en-us/graph/throttling-limits)
- [Register an application](https://learn.microsoft.com/en-us/graph/auth-register-app-v2)
- [msgraph-sdk-python GitHub](https://github.com/microsoftgraph/msgraph-sdk-python)
