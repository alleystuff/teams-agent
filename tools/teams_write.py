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


@tool
def post_chat_message(chat_id: str, message: str) -> str:
    """Post a plain-text message to a Microsoft Teams chat (1:1 or group chat).

    Args:
        chat_id: The Teams chat ID (e.g. 19:xxxx@thread.v2).
        message: The plain-text message content to post.

    Returns:
        The ID of the created message.
    """
    async def _post():
        body = ChatMessage(body=ItemBody(content=message))
        result = await graph.chats.by_chat_id(chat_id).messages.post(body)
        return result.id
    return asyncio.run(_post())
