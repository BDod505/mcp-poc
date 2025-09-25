import asyncio
from langchain_ollama import ChatOllama
from mcp_use import MCPAgent,MCPClient

async def main():
    config = {
        "mcpServers": {
            "poc-tools":{
                "url":"http://localhost:8000/mcp"
            }
        }
    }

    client = MCPClient.from_dict(config)
    llm = ChatOllama(model="llama3.2:1b",base_url="http://localhost:11434")
    agent = MCPAgent(llm=llm,client=client, max_steps=20)

    result = await agent.run(
        "Query the MongoDB for movies with quantity greater than 3 and summarize the resilts"
    )
    print(f"\nResult: {result}")

    await client.close_all_sessions()

if __name__=="__main__":
    asyncio.run(main())
