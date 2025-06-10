import json
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from datetime import date

# Load environment variables
load_dotenv()
endpoint = os.getenv("AZURE_OPENAI_API_ENDPOINT")
deployment = os.getenv("MODEL_DEPLOYMENT_NAME")
api_key = os.getenv("AZURE_OPENAI_API_KEY")

# Initialize Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=api_key,
    api_version="2025-01-01-preview",
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

# --- Function Map ---
function_map = {
    "getWeather": getWeather,
    "searchFlight": searchFlight,
    "bookHotel": bookHotel
}

# --- OpenAI Function Schemas ---
functions = [
    {
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
    },
    {
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
    },
    {
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
]

# --- Prompt Examples ---
example_prompts = [
    "I need a flight from Paris to Rome on June 20th.",
    "Can you book a hotel in Barcelona from July 10 to July 15?",
    "What is the weather like in New York in Fahrenheit?",
    "I'm thinking about visiting Rome this summer. What do you recommend I do there?"
]

# --- Choose one to test ---
selected_prompt = example_prompts[3]  # Change to [1] or [2] or [3]

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

# --- Run OpenAI Chat Completion ---
completion = client.chat.completions.create(
    model=deployment,
    messages=chat_prompt,
    functions=functions,
    function_call="auto"
)

assistant_response = completion.choices[0].message

# --- Output response ---
print("Assistant Response:", assistant_response)
print("Function Call:", assistant_response.function_call)

# --- Handle Function Call ---
if assistant_response.function_call:
    function_name = assistant_response.function_call.name
    function_args = json.loads(assistant_response.function_call.arguments)

    print(f"🔧 Calling function: {function_name} with arguments: {function_args}")

    func = function_map.get(function_name)
    if func:
        result = func(**function_args)
        print(f"Function {function_name} result:", result)
    else:
        print(f"Function {function_name} not found.")
else:
    print("ℹNo function call detected.")