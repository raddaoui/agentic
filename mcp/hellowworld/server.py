from mcp.server.fastmcp import FastMCP
from starlette.requests import Request

# Create an MCP server
mcp = FastMCP(name="HelloWorldServer", 
              host="0.0.0.0",
              port=8080)


# Add a tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a resource to retrieve document content
# Static resource (no template) — this *will* show in session.list_resources()
@mcp.resource("file://documents/hello.txt")
def read_hello() -> str:
    """A static hello file."""
    return "Hello, static file!"

# Dynamic resource template - this *will not* show in session.list_resource_templates()
@mcp.resource("file://documents/{name}")
def read_document(name: str) -> str:
    """Read a document by name via template."""
    return f"Dynamic content of {name}"


# Add a prompt for code review
@mcp.prompt(title="Code Review")
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"



if __name__ == "__main__":
    import os
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    print(f"Starting MCP server ({transport}) on 0.0.0.0:8080")
    mcp.run(transport=transport)
