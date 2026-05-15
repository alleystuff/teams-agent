import os
from dotenv import load_dotenv

load_dotenv(override=True)  # Must be called before tool imports; tools execute get_graph_client() at module level

from azure.identity import get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools.teams_read import read_channel_messages
from tools.teams_write import post_channel_message, post_chat_message
from auth import get_foundry_credential

token_provider = get_bearer_token_provider(
    get_foundry_credential(), "https://cognitiveservices.azure.com/.default"
)

llm = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_AI_ENDPOINT"],
    azure_deployment=os.environ.get("AZURE_AI_DEPLOYMENT", "gpt-4o"),
    api_version=os.environ.get("AZURE_AI_API_VERSION", "2024-12-01-preview"),
    azure_ad_token_provider=token_provider,
)

tools = [read_channel_messages, post_channel_message, post_chat_message]

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
