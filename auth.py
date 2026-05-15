from __future__ import annotations

import os
from azure.identity import ClientSecretCredential, DefaultAzureCredential, DeviceCodeCredential
from msgraph import GraphServiceClient

_graph_client: GraphServiceClient | None = None


def get_foundry_credential() -> ClientSecretCredential | DefaultAzureCredential:
    """Returns Azure credential for AI Foundry.

    Uses ClientSecretCredential when TEAMS_CLIENT_SECRET is set (service principal),
    otherwise falls back to DefaultAzureCredential (az login / managed identity).
    """
    client_secret = os.environ.get("TEAMS_CLIENT_SECRET")
    if client_secret:
        return ClientSecretCredential(
            tenant_id=os.environ["TEAMS_TENANT_ID"],
            client_id=os.environ["TEAMS_CLIENT_ID"],
            client_secret=client_secret,
        )
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
            "https://graph.microsoft.com/ChannelMessage.Send",
            "https://graph.microsoft.com/ChannelMessage.Read.All",
            "https://graph.microsoft.com/Chat.ReadWrite",
            "https://graph.microsoft.com/Team.ReadBasic.All",
            "https://graph.microsoft.com/Channel.ReadBasic.All",
        ]
        _graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
    return _graph_client
