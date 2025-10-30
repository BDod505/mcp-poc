import asyncio
import json
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

async def extract_tool_output(resp):
    """Safely extract and parse tool output from CallToolResult object."""
    if hasattr(resp, "content") and resp.content:
        # MCP responses often store text in content[0].text
        first_item = resp.content[0]
        text_output = getattr(first_item, "text", str(first_item))
    else:
        text_output = str(resp)

    # Try to parse JSON
    try:
        parsed = json.loads(text_output)
        return parsed
    except json.JSONDecodeError:
        print("Non-JSON tool response:", text_output)
        return text_output


async def main():
    # Start MCP server (server.py)
    server_params = StdioServerParameters(
    command="python",
    args=["server.py"],)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # List available tools
            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])

            # Convert natural language query -> MongoDB filter
            nl_q = "red cotton dresses for women for summer under 2000"
            resp = await session.call_tool("nl_to_mongo_filter", {"nl_query": nl_q})
            filt = await extract_tool_output(resp)
            print("\n Filter generated:\n", filt)

            # Search products from MongoDB
            products_resp = await session.call_tool(
            "search_products", {"filter_json": filt, "limit": 5}
            )
            products = await extract_tool_output(products_resp)
            print("\n Products found:\n", products)

            #Summarize results for user
            summary_resp = await session.call_tool("summarize_products", {"product_docs_json": json.dumps(products)})
            summary = await extract_tool_output(summary_resp)
            print("\n --- Summary for user ---\n", summary)


if __name__ == "__main__":
    asyncio.run(main())