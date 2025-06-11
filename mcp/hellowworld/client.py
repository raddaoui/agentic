from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import PromptReference

server_endpoint = "http://127.0.0.1:8080/mcp"
headers = {}

async def run():
    async with streamablehttp_client(url=server_endpoint, headers=headers) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize connection
            await session.initialize()

            # List available prompts
            prompts = await session.list_prompts()
            print("\nAvailable prompts:")
            for prompt in prompts.prompts:
                print(prompt)

            # Call the "review_code" prompt
            prompt = await session.get_prompt(
                "review_code",
                arguments={"code": "def add(a, b): return a + b"},
            )
            print("\nResult of prompt:", prompt)

            # List resources
            resources = await session.list_resources()
            print("\nAvailable resources:", resources)
            res_list = await session.list_resources()

            # List available resource templates
            templates = await session.list_resource_templates()
            print("Available resource templates:")
            for template in templates.resourceTemplates:
                print(f"  - {template.uriTemplate}")
                

            # Try reading the static resource
            print("\nReading static resource hello.txt:")
            content, mime = await session.read_resource("file://documents/hello.txt")
            print("  content:", content, "mime:", mime)

            # Try reading via template
            print("\nReading resource template (name = example.md):")
            content2, mime2 = await session.read_resource("file://documents/example.md")
            print("  content:", content2, "mime:", mime2)


            # List tools
            tools = await session.list_tools()
            print("\nAvailable tools:", tools)

            # Call the add tool
            result = await session.call_tool("add", arguments={"a": 2, "b": 3})
            print("Result of add tool:", result)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
