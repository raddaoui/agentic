# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    This sample demonstrates how to use agent operations with the Bing grounding tool from
    the Azure Agents service using a synchronous client.

USAGE:
    python sample_agents_bing_grounding.py

    Before running the sample:

    pip install azure-ai-projects azure-identity

    Set these environment variables with your own values:
    1) PROJECT_CONNECTION_STRING - The project connection string, as found in the overview page of your
       Azure AI Foundry project.
    2) MODEL_DEPLOYMENT_NAME - The deployment name of the AI model, as found under the "Name" column in 
       the "Models + endpoints" tab in your Azure AI Foundry project.
    3) BING_CONNECTION_NAME - The connection name of the Bing connection, as found in the 
       "Connected resources" tab in your Azure AI Foundry project.
"""

import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MessageRole, BingGroundingTool
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import logging
import os

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

load_dotenv()

AGENT_NAME = "Web Search Agent"
API_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")
PROJECT_CONNECTION_STRING = os.environ["PROJECT_CONNECTION_STRING"]
BING_CONNECTION_NAME = os.getenv("BING_CONNECTION_NAME")
MAX_COMPLETION_TOKENS = 4096
MAX_PROMPT_TOKENS = 10240
TEMPERATURE = 0.1
TOP_P = 0.1


project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=PROJECT_CONNECTION_STRING,
)

INSTRUCTIONS_FILE = "instructions/instructions_bing_grounding.txt"
INSTRUCTIONS_FILE_PATH = INSTRUCTIONS_FILE
with open(INSTRUCTIONS_FILE_PATH, "r", encoding="utf-8", errors="ignore") as file:
    instructions = file.read()

bing_connection = project_client.connections.get(connection_name=BING_CONNECTION_NAME)
conn_id = bing_connection.id

# Initialize agent bing tool and add the connection id
bing = BingGroundingTool(connection_id=conn_id)

# Create agent with the bing tool and process assistant run
with project_client:
    agent = project_client.agents.create_agent(
        model=API_DEPLOYMENT_NAME,
        name=AGENT_NAME,
        instructions=instructions,
        tools=bing.definitions,
        temperature=TEMPERATURE,
        headers={"x-ms-enable-preview": "true"},
    )
    # [END create_agent_with_bing_grounding_tool]

    print(f"Created agent, ID: {agent.id}")

    # Create thread for communication
    thread = project_client.agents.create_thread()
    print(f"Created thread, ID: {thread.id}")

    # Create message to thread
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role=MessageRole.USER,
        content="Can you provide a list of fires that occurred in Los Angeles in 2025?",
    )
    print(f"Created message, ID: {message.id}")

    # Ask the agent to perform work on the thread
    run = project_client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
    print(f"Run finished with status: {run.status}")

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")

    # Delete the assistant when done
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")

    # Print the Agent's response message with optional citation
    response_message = project_client.agents.list_messages(thread_id=thread.id).get_last_message_by_role(
        MessageRole.AGENT
    )
    
    if response_message:
        for text_message in response_message.text_messages:
            print(f"Agent response: {text_message.text.value}")
        # Check for annotations
        if hasattr(text_message.text, 'annotations'):
            for annotation in text_message.text.annotations:
                if annotation.type == "url_citation":
                    print(f"🔗 Source: {annotation.url_citation.title} — {annotation.url_citation.url}")