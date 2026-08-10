"""
Open-Meteo API integration for weather data.

This module provides a thin wrapper around the Open-Meteo geocoding
and forecast APIs. It keeps all HTTP requests and response parsing
separate from the MCP tool functions.

Geocoding endpoint:
GET https://geocoding-api.open-meteo.com/v1/search

Forecast endpoint:
GET https://api.open-meteo.com/v1/forecast
"""

import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _resolve_location(location: str) -> dict:
    """
    Resolve a city or place name into latitude and longitude.

    Args:
        location: City or place name, e.g. "Chicago, IL".

    Returns:
        A dict containing name, country, latitude, longitude, and timezone.

    Raises:
        RuntimeError: If the location cannot be resolved or the API fails.
    """
    location = location.strip()

    if not location:
        raise ValueError("Location cannot be empty.")

    try:
        response = requests.get(
            GEOCODING_URL,
            params={
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            raise RuntimeError(f"No location found for '{location}'.")

        result = results[0]

        return {
            "name": result["name"],
            "country": result.get("country"),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "timezone": result.get("timezone"),
        }

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Failed to resolve location '{location}': {e}"
        )


def get_current_weather(location: str) -> dict:
    """
    Get current weather conditions for a location.

    Args:
        location: City or place name, e.g. "Chicago, IL".

    Returns:
        A dict with location, temperature, apparent temperature,
        humidity, wind speed, and weather code.

    Raises:
        RuntimeError: If weather data cannot be retrieved.
    """
    place = _resolve_location(location)

    try:
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "auto",
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        current = data.get("current")

        if not current:
            raise RuntimeError(
                f"No current weather returned for '{location}'."
            )

        return {
            "location": place["name"],
            "country": place["country"],
            "temperature_f": current.get("temperature_2m"),
            "feels_like_f": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_mph": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
            "as_of": current.get("time"),
        }

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Failed to fetch current weather for '{location}': {e}"
        )


def get_forecast(location: str, days: int = 5) -> dict:
    """
    Get a multi-day weather forecast.

    Args:
        location: City or place name.
        days: Number of forecast days to return, from 1 through 7.

    Returns:
        A dict containing location information and daily forecasts.

    Raises:
        ValueError: If days is outside the supported range.
        RuntimeError: If forecast data cannot be retrieved.
    """
    if days < 1 or days > 7:
        raise ValueError("days must be between 1 and 7.")

    place = _resolve_location(location)

    try:
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": (
                    "weather_code,"
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max,"
                    "wind_speed_10m_max"
                ),
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "auto",
                "forecast_days": days,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        daily = data.get("daily")

        if not daily:
            raise RuntimeError(
                f"No forecast returned for '{location}'."
            )

        forecasts = []

        for i, date in enumerate(daily["time"]):
            forecasts.append(
                {
                    "date": date,
                    "high_f": daily["temperature_2m_max"][i],
                    "low_f": daily["temperature_2m_min"][i],
                    "precipitation_probability": (
                        daily["precipitation_probability_max"][i]
                    ),
                    "wind_mph": daily["wind_speed_10m_max"][i],
                    "weather_code": daily["weather_code"][i],
                }
            )

        return {
            "location": place["name"],
            "country": place["country"],
            "forecast": forecasts,
        }

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Failed to fetch forecast for '{location}': {e}"
        )


def get_travel_recommendation(location: str, date: str) -> dict:
    """
    Generate a simple weather-based travel recommendation.

    Rules:
        - Recommend an umbrella when precipitation probability >= 40%.
        - Recommend a jacket when the forecast high is below 60°F.
        - Warn about wind when maximum wind speed exceeds 25 mph.
        - Recommend hydration when the forecast high is at least 85°F.

    Args:
        location: City or place name.
        date: Forecast date in YYYY-MM-DD format.

    Returns:
        A dict containing the day's forecast, recommendations, and reasons.

    Raises:
        RuntimeError: If the requested date is not available.
    """
    forecast_data = get_forecast(location, days=7)

    matching_day = next(
        (
            day
            for day in forecast_data["forecast"]
            if day["date"] == date
        ),
        None,
    )

    if matching_day is None:
        raise RuntimeError(
            f"No forecast available for '{location}' on {date}."
        )

    recommendations = []
    reasons = []

    rain_chance = matching_day["precipitation_probability"]
    high = matching_day["high_f"]
    wind = matching_day["wind_mph"]

    if rain_chance is not None and rain_chance >= 40:
        recommendations.append("Bring an umbrella.")
        reasons.append(
            f"Precipitation probability is {rain_chance}%, "
            "which meets the 40% umbrella threshold."
        )

    if high is not None and high < 60:
        recommendations.append("Bring a jacket.")
        reasons.append(
            f"The forecast high is {high}°F."
        )

    if wind is not None and wind > 25:
        recommendations.append(
            "Prepare for windy conditions."
        )
        reasons.append(
            f"Maximum forecast wind is {wind} mph."
        )

    if high is not None and high >= 85:
        recommendations.append(
            "Dress lightly and stay hydrated."
        )
        reasons.append(
            f"The forecast high is {high}°F."
        )

    if not recommendations:
        recommendations.append(
            "No special weather gear is recommended."
        )
        reasons.append(
            "The forecast does not cross any recommendation thresholds."
        )

    return {
        "location": forecast_data["location"],
        "country": forecast_data["country"],
        "date": date,
        "forecast": matching_day,
        "recommendations": recommendations,
        "reasons": reasons,
    }