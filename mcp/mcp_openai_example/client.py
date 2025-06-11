import os
import json
import asyncio
import logging
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import AzureOpenAI
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# ─── Configuration / Logging Setup ────────────────────────────────────

load_dotenv(".env")

SERVER_ENDPOINT = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8080/mcp")
HEADERS: Dict[str, str] = {}

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_API_ENDPOINT")
AZURE_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")

if not AZURE_API_KEY:
    raise RuntimeError("Missing AZURE_OPENAI_API_KEY in environment")

# Base logger
logger = logging.getLogger("my_app")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

class AppLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        # Prepend an “[APP]” tag (you could use different tags or logic)
        return f"[APP] {msg}", kwargs

app_logger = AppLoggerAdapter(logger, {})

# Initialize Azure OpenAI client
azure_client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version="2025-01-01-preview",
)

BASE_PROMPT = [
    {"role": "system", "content": "You are an AI assistant that helps people find information."},
    {"role": "user", "content": "what is the weather in New York?"},
]


def sync_openai_call(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    tool_choice: str,
) -> Any:
    return azure_client.chat.completions.create(
        model=AZURE_DEPLOYMENT,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
    )


async def call_openai_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    tool_choice: str = "auto"
) -> Any:
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(
        None, sync_openai_call, messages, tools, tool_choice
    )
    return resp


async def convert_mcp_tools_to_openai(tools_obj: Any) -> List[Dict[str, Any]]:
    result = []
    for tool in getattr(tools_obj, "tools", []):
        result.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            }
        })
    return result


async def run():
    app_logger.info("Starting MCP + OpenAI integration run")

    async with streamablehttp_client(url=SERVER_ENDPOINT, headers=HEADERS) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            try:
                await session.initialize()
                app_logger.info("MCP session initialized")
            except Exception as e:
                logger.error("Failed to initialize MCP session: %s", e)
                return

            try:
                tools_obj = await session.list_tools()
                app_logger.info("Listed MCP tools: %s", tools_obj)
            except Exception as e:
                logger.error("Failed to list MCP tools: %s", e)
                return

            # Convert MCP tools to OpenAI format
            openai_tools = await convert_mcp_tools_to_openai(tools_obj)
            app_logger.info("Converted tools to OpenAI format: %s", openai_tools)

            messages = list(BASE_PROMPT)

            app_logger.info("Calling OpenAI with tool_choice=auto …")
            try:
                completion = await call_openai_with_tools(messages, openai_tools, "auto")
            except Exception as e:
                logger.error("OpenAI call failed: %s", e)
                return

            assistant_msg = completion.choices[0].message
            app_logger.info("Received assistant message: %s", assistant_msg)

            messages.append(assistant_msg)

            if assistant_msg.tool_calls:
                for call in assistant_msg.tool_calls:
                    fname = call.function.name
                    raw_args = call.function.arguments
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON in tool arguments: %s", raw_args)
                        continue

                    app_logger.info("Invoking MCP tool '%s' with args: %s", fname, args)
                    try:
                        tool_result = await session.call_tool(fname, arguments=args)
                        app_logger.info("Result from tool '%s': %s", fname, tool_result)
                    except Exception as e:
                        logger.error("Tool call %s failed: %s", fname, e)
                        continue

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": tool_result.content[0].text
                    })

                app_logger.info("Messages after processing tool calls: %s", messages)

                app_logger.info("Calling OpenAI final completion")
                try:
                    final_completion = await call_openai_with_tools(messages, openai_tools, "auto")
                    final_msg = final_completion.choices[0].message
                    app_logger.info("Final assistant reply: %s", final_msg.content)
                except Exception as e:
                    logger.error("Final OpenAI call failed: %s", e)


if __name__ == "__main__":
    asyncio.run(run())
