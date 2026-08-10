"""
Weather forecast MCP server.

Exposes weather tools over MCP so a Databricks Agent Bricks agent
can answer current-weather, forecast, and travel recommendation questions.

Tools:
    - get_current_weather(location)
    - get_forecast(location, days)
    - get_travel_recommendation(location, date)

Weather data is provided by Open-Meteo through weather_broker.py.

Run locally:
    python weather_mcp_server.py
"""

import os
import logging

from fastmcp import FastMCP

import weather_broker


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather-mcp-server")


mcp = FastMCP("weather-prediction")


@mcp.tool
def get_current_weather(location: str) -> dict:
    """
    Get current weather conditions for a location.

    Args:
        location: City or place name, e.g. "Chicago" or "Austin, TX".

    Returns:
        A dict containing location, temperature, apparent temperature,
        humidity, wind speed, weather code, and observation time.
    """
    try:
        return weather_broker.get_current_weather(location)
    except Exception as e:
        logger.exception("Failed to get current weather")
        return {
            "status": "error",
            "message": str(e),
        }


@mcp.tool
def get_forecast(location: str, days: int = 5) -> dict:
    """
    Get a multi-day weather forecast.

    Args:
        location: City or place name, e.g. "Chicago".
        days: Number of forecast days to return, from 1 through 7.

    Returns:
        A dict containing daily high and low temperatures,
        precipitation probability, wind speed, and weather code.
    """
    try:
        return weather_broker.get_forecast(location, days)
    except Exception as e:
        logger.exception("Failed to get weather forecast")
        return {
            "status": "error",
            "message": str(e),
        }


@mcp.tool
def get_travel_recommendation(location: str, date: str) -> dict:
    """
    Generate a simple weather-based travel recommendation.

    The recommendation is derived from forecast data rather than simply
    repeating the API response.

    Rules include:
        - Bring an umbrella when precipitation probability is >= 40%.
        - Bring a jacket when the forecast high is below 60 F.
        - Warn about windy conditions when maximum wind exceeds 25 mph.
        - Recommend hydration when the forecast high is at least 85 F.

    Args:
        location: City or place name, e.g. "Seattle".
        date: Forecast date in YYYY-MM-DD format.

    Returns:
        A dict containing the selected day's forecast,
        recommendations, and explanations.
    """
    try:
        return weather_broker.get_travel_recommendation(location, date)
    except Exception as e:
        logger.exception("Failed to create travel recommendation")
        return {
            "status": "error",
            "message": str(e),
        }


if __name__ == "__main__":
    port = int(
        os.getenv(
            "DATABRICKS_APP_PORT",
            os.getenv("PORT", 8000),
        )
    )

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port,
        stateless_http=True,
    )