import asyncio
from langchain_core.tools import tool
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.teams.item.channels.item.messages.messages_request_builder import MessagesRequestBuilder
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
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(top=top)
        config = RequestConfiguration(query_parameters=query_params)
        result = await graph.teams.by_team_id(team_id) \
            .channels.by_channel_id(channel_id) \
            .messages.get(request_configuration=config)
        return [
            {
                "from": m.from_.user.display_name if m.from_ and m.from_.user else "unknown",
                "body": m.body.content if m.body else "",
                "createdDateTime": str(m.created_date_time),
            }
            for m in (result.value or [])
        ]
    return asyncio.run(_fetch())
