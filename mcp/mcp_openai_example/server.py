from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="WeatherMCPServer", host="0.0.0.0", port=8080)

@mcp.tool()
def get_weather(city: str) -> str:
    """
    Get the current weather for a specified city.
    
    :param city: The name of the city to get the weather for.
    :return: A string describing the current weather in the city.
    """
    # Simulated weather data for demonstration purposes
    weather_data = {
        "New York": "Sunny, 25°C",
        "Los Angeles": "Cloudy, 22°C",
        "Chicago": "Rainy, 18°C"
    }
    
    return weather_data.get(city, "Weather data not available for this city.")

if __name__ == "__main__":
    import os
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    print(f"Starting Weather MCP server ({transport}) on 0.0.0.0:8080")
    mcp.run(transport=transport)


