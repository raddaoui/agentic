import json
import os
from datetime import date
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()
endpoint = os.getenv("AZURE_OPENAI_API_ENDPOINT")
deployment = os.getenv("MODEL_DEPLOYMENT_NAME")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY")

# Initialize Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2024-04-01-preview",  # Must be >= 2024-04-01-preview
)

# --- Mock Functions ---
def getWeather(location, unit="celsius"):
    print(f"[MOCK] Getting weather for {location} in {unit}")
    return {"location": location, "temperature": "25", "unit": unit}

def searchFlight(from_, to, date):
    print(f"[MOCK] Searching flights from {from_} to {to} on {date}")
    return {"flights": ["Flight123", "Flight456"], "date": date}

def bookHotel(city, check_in, check_out):
    print(f"[MOCK] Booking hotel in {city} from {check_in} to {check_out}")
    return {"confirmation": "HOTEL123", "city": city}

# --- Function mapping ---
function_map = {
    "getWeather": getWeather,
    "searchFlight": searchFlight,
    "bookHotel": bookHotel
}

# --- Tools Schema ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "getWeather",
            "description": "Get the current weather for a given location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name, e.g. 'London'"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "searchFlight",
            "description": "Search for available flights between two cities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_": {"type": "string", "description": "Departure city"},
                    "to": {"type": "string", "description": "Arrival city"},
                    "date": {"type": "string", "description": "Date of travel in YYYY-MM-DD"}
                },
                "required": ["from_", "to", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bookHotel",
            "description": "Book a hotel in a given city on specific dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "check_in": {"type": "string"},
                    "check_out": {"type": "string"}
                },
                "required": ["city", "check_in", "check_out"]
            }
        }
    }
]


# --- Prompt Examples ---
example_prompts = [
    "I need a flight from Paris to Rome on June 20th.",
    "Can you book a hotel in Barcelona from July 10 to July 15?",
    "What is the weather like in New York in Fahrenheit?",
    "I need to fly from San Francisco to Tokyo on July 15th, and also book a hotel in Tokyo from July 15th to July 20th.",
    "I'm thinking about visiting Rome this summer. What do you recommend I do there?"
]

# --- Choose one to test ---
selected_prompt = example_prompts[4]  # Change to [1] or [2] or [3] or [4]

chat_prompt = [
    {
        "role": "system",
        "content": f"You are an AI assistant that helps people with travel planning and provide travel recommendations. Today is {date.today().strftime('%B %d, %Y')}. You can provide weather information, search for flights, and book hotels."
    },
    {
        "role": "user",
        "content": selected_prompt
    }
]

# --- Chat Completion Call ---
completion = client.chat.completions.create(
    model=deployment,
    messages=chat_prompt,
    tools=tools,
    tool_choice="auto"
)

assistant_response = completion.choices[0].message

# --- Output response ---
print("Assistant Response:\n", assistant_response.content)
print("Tool Calls:\n", assistant_response.tool_calls)

# --- Handle tool calls ---
if assistant_response.tool_calls:
    for tool_call in assistant_response.tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        print(f"Calling {function_name} with arguments: {function_args}")
        if function_name in function_map:
            result = function_map[function_name](**function_args)
            print(f"Result: {result}")
        else:
            print(f"Function {function_name} not found.")