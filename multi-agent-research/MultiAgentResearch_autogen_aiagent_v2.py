# Standard libraries
import os
import json
import asyncio
import datetime

# Load environment variables from .env file
from dotenv import load_dotenv

# Rich is used for better console output formatting
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown

# Azure SDK and tools
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MessageRole, BingGroundingTool

# AutoGen-related modules for multi-agent chat
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
# Azure OpenAI wrapper for model communication
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.tools.code_execution import PythonCodeExecutionTool

# Load environment variables into a dictionary
dotenv_path = load_dotenv()
env = {
    'project_conn': os.getenv('PROJECT_CONNECTION_STRING'),
    'bing_conn_name': os.getenv('BING_CONNECTION_NAME'),
    'azure_endpoint': os.getenv('AZURE_OPENAI_API_ENDPOINT'),
    'azure_key': os.getenv('AZURE_OPENAI_API_KEY'),
    'model_deployment': os.getenv('MODEL_DEPLOYMENT_NAME'),
    'api_version': os.getenv('AZURE_OPENAI_API_VERSION'),
}

# Asynchronous function to fetch web search snippets using Bing via Azure AI agent
async def get_bing_snippet(query: str) -> str:
    # Create AI project client using default Azure credentials
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=env['project_conn']
    )

    # Load grounding instructions for Bing tool
    INSTRUCTIONS_PATH = 'instructions/instructions_bing_grounding.txt'
    with open(INSTRUCTIONS_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        INSTRUCTIONS = f.read().strip()

    # Helper function to parse and extract citation annotations
    def parse_annotations(block):
        text = block['text']['value'].strip()
        annotations = block['text'].get('annotations', [])
        entries = []
        if annotations:
            for ann in annotations:
                if ann.get('type') == 'url_citation':
                    url = ann['url_citation'].get('url', 'No URL found')
                    title = ann['url_citation'].get('title', 'No title found')
                    entries.append({'text': text, 'url': url, 'title': title})
        else:
            entries.append({'text': text, 'url': 'No URL found', 'title': 'No title found'})
        return entries
    
    # Create Bing grounding tool from specified connection
    bing = BingGroundingTool(
        connection_id=project_client.connections.get(
            connection_name=env['bing_conn_name']
        ).id
    )

    # Register a temporary agent with Bing tool and instructions
    agent = project_client.agents.create_agent(
        model=env['model_deployment'],
        name='web_search_agent',
        instructions=INSTRUCTIONS,
        tools=bing.definitions,
        temperature=0.1,
        headers={'x-ms-enable-preview': 'true'}
    )

    # Create thread and submit user query to the agent
    thread = project_client.agents.create_thread()
    project_client.agents.create_message(thread_id=thread.id, role=MessageRole.USER, content=query)
    project_client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)

    # Clean up by deleting the temporary agent
    project_client.agents.delete_agent(agent.id)

    # Retrieve the agent's response messages
    response = project_client.agents.list_messages(thread_id=thread.id).get_last_message_by_role(MessageRole.AGENT)

    # Parse and return annotated results
    results = []
    if response:
        for block in response.text_messages:
            if block.get('type') == 'text':
                results.extend(parse_annotations(block))

    return json.dumps(results, indent=2)

# Main orchestration logic for multi-agent workflow
async def main():
    console = Console()

    model_client=AzureOpenAIChatCompletionClient(
            model=env['model_deployment'],
            api_version=env['api_version'],
            azure_endpoint=env['azure_endpoint'],
            api_key=env['azure_key'],
            model_info={'vision': True, 'function_calling': True, 'json_output': True, 'structured_output': True, 'family': 'gpt-4o'},

    )

    # Define all assistant agents with specific roles

    # Instantiate user proxy (simulated user interface)
    user_proxy = UserProxyAgent('User')

    web_search_agent = AssistantAgent(
        name='web_search_agent',
        description='An agent who can search the web to conduct research and answer open questions',
        model_client=model_client,
        system_message='You are an agent who can search the web to conduct research and answer open questions.  You can use the bing tool to search the internet for information.  You should return a list of entries with text, url, and title for each entry. Never reply with Terminate, just return the list of entries.',
        tools=[get_bing_snippet]
    )

    writer_assistant = AssistantAgent(
        name='writer_assistant',
        description='A high-quality journalist agent who excels at writing a first draft of an article as well as revising the article based on feedback from the other agents',
        model_client=model_client,
        system_message='You are a high-quality journalist agent who excels at writing a first draft of an article as well as revising the article based on feedback from the other agents.  Do not just write bullet points on how you would write the article, but actually write it.  You can also ask for research to be conducted on certain topics.'
    )

    editor_agent = AssistantAgent(
        name='editor',
        description='An expert editor of written articles who can read an article and make suggestions for improvements',
        model_client=model_client,
        system_message='You are an expert editor.  You carefully read an article and make suggestions for improvements and suggest additional topics that should be researched to improve the article quality.'
    )

    verifier_agent = AssistantAgent(
        name='verifier_agent',
        description='A responsible agent who will verify the facts and ensure that the article is accurate and well-written',
        model_client=model_client,
        system_message='Ensure article accuracy and approve or reject with reasons. you should use the bing tool to search the internet to verify any relevant facts. and explicitly approve or reject the article based on accuracy, giving your reasoning. You can ask for rewrites if you find inaccuracies.',
        tools=[get_bing_snippet]
    )
    code_execution = PythonCodeExecutionTool(LocalCommandLineCodeExecutor(work_dir="coding"))

    orchestrator_agent = AssistantAgent(
        name='orchestrator_agent',
        description='Team leader who verifies when the article is complete and meets all requirements',
        model_client=model_client,
        system_message="You are a leading a journalism team that conducts research to craft high-quality articles. If the article isn't well written, ask the writer for a rewrite. any article needs to be reviewed by the editor, and has been fact-checked and approved by the verifier agent, and approved by the user, then create python code to store the article to a file locally in markdown. once executed reply 'TERMINATE'.  Otherwise state what condition has not yet been met.",
        tools=[code_execution]
    )

    # Termination condition: look for the keyword 'TERMINATE' to end the session
    text_mention_termination = TextMentionTermination("TERMINATE")
    max_messages_termination = MaxMessageTermination(max_messages=30)
    termination = text_mention_termination | max_messages_termination

    # Define the group of agents that will collaborate
    agent_team = SelectorGroupChat(
        [writer_assistant, web_search_agent, editor_agent, verifier_agent, user_proxy, orchestrator_agent],
        model_client=model_client,
        termination_condition=termination,
        allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
    )

    # Task prompt for the orchestrator to start the session
    task_prompt = (
        'Ask the user to describe the article they want. '
        f"Today's date is {datetime.date.today()}"
    )

    # Run the session and stream outputs to the console
    async for response in agent_team.run_stream(task=task_prompt):
        if isinstance(response, TaskResult):
            console.print(response.stop_reason)
        else:
            console.print(Text(f'{response.source}: ', style='bold magenta'), end='')
            if isinstance(response.content, str):
                console.print(Markdown(response.content))
            else:
                console.print(response.content)

# Entry point for the script
if __name__ == '__main__':
    asyncio.run(main())