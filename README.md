# Weather Prediction MCP Server + Agent

A weather forecasting and recommendation system built with **FastMCP**, **Open-Meteo**, **Databricks Apps**, **Unity AI Gateway**, and a **Databricks Agent Bricks Supervisor Agent**.

This project was created as part of the Day 3 MCP Server + Agent homework. It follows the architecture demonstrated in the `databricks-lakebase-app-day-3` project while replacing the stock-trading use case with a custom weather prediction system.

The project includes:

* A custom FastMCP weather server
* A separate weather API adapter/broker
* Three weather MCP tools
* Open-Meteo integration
* A Databricks-hosted MCP server
* Unity AI Gateway MCP registration
* A Databricks Supervisor Agent
* Weather-based prediction and recommendation logic
* An optional weather dashboard deployed as a separate Databricks App

---

## Architecture

```text
                         User
                           |
                           v
                +----------------------+
                | Databricks Supervisor|
                |        Agent         |
                +----------+-----------+
                           |
                           | MCP tool call
                           v
                +----------------------+
                |   Unity AI Gateway   |
                | mcp-weather-prediction|
                +----------+-----------+
                           |
                           | Streamable HTTP
                           v
                +----------------------+
                |   Databricks App     |
                |   FastMCP Server     |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |  weather_broker.py   |
                | API + parsing layer  |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |      Open-Meteo      |
                | Weather + Geocoding  |
                +----------------------+
```

The optional dashboard is deployed separately:

```text
User
 |
 v
+-----------------------+
| Weather Dashboard App |
|        Flask          |
+-----------+-----------+
            |
            v
+-----------------------+
|   weather_broker.py   |
+-----------+-----------+
            |
            v
+-----------------------+
|      Open-Meteo       |
+-----------------------+
```

---

## Project Structure

```text
Weather-Prediction-MCP-Server-Agent/
│
├── weather_broker.py
├── weather_mcp_server.py
├── requirements.txt
├── app.yaml
├── system_prompt.md
├── README.md
│
├── screenshots/
│   ├── current-weather.png
│   ├── forecast.png
│   └── recommendation.png
│
└── dashboard/
    ├── app.py
    ├── weather_broker.py
    ├── app.yaml
    ├── requirements.txt
    │
    └── templates/
        └── index.html
```

---

# Weather API

## Open-Meteo

This project uses **Open-Meteo** as the weather data provider.

Open-Meteo was selected because:

* No API key is required
* No credit card is required
* No signup is required
* It provides current and forecast weather data
* It provides a geocoding API for converting city names into coordinates

Because Open-Meteo does not require authentication, this project does not need to store an API key or weather API credentials in Databricks Secrets.

This also prevents API credentials from being accidentally committed to Git.

---

# Broker / Adapter Layer

All communication with Open-Meteo is handled by:

```text
weather_broker.py
```

The broker is responsible for:

* Resolving location names
* Calling Open-Meteo
* Parsing API responses
* Converting weather data into clean Python dictionaries
* Performing recommendation logic
* Handling API and location errors

The MCP server itself does not make raw HTTP requests.

This keeps the architecture separated into:

```text
MCP Tool
   |
   v
Broker / Adapter
   |
   v
External Weather API
```

This follows the same general separation of responsibilities as the broker pattern from the Day 3 project.

---

# MCP Server

The MCP server is implemented using **FastMCP**.

The server is defined in:

```text
weather_mcp_server.py
```

It exposes weather functionality using `@mcp.tool` decorated functions and runs using HTTP transport so that Databricks can connect to it as an external MCP server.

The deployed MCP endpoint follows the pattern:

```text
https://<databricks-app-url>/mcp
```

---

# MCP Tools

The project implements the three required weather capabilities.

## 1. `get_current_weather`

```python
get_current_weather(location: str)
```

Returns current weather conditions for a location.

Example question:

```text
What's the weather in Chicago right now?
```

Example data returned by the tool includes:

* Location
* Country
* Temperature
* Feels-like temperature
* Humidity
* Wind speed
* Weather code
* Observation time

Example:

```json
{
  "location": "Chicago",
  "country": "United States",
  "temperature_f": 71.2,
  "feels_like_f": 77.1,
  "humidity_percent": 93,
  "wind_mph": 3.7,
  "weather_code": 0,
  "as_of": "2026-08-09T21:00"
}
```

---

## 2. `get_forecast`

```python
get_forecast(location: str, days: int = 5)
```

Returns a multi-day weather forecast.

Example question:

```text
Will it rain in Austin tomorrow?
```

The forecast includes:

* Date
* Daily high temperature
* Daily low temperature
* Precipitation probability
* Wind speed
* Weather code

The Agent can use these values to answer natural-language questions about future weather.

---

## 3. `get_travel_recommendation`

```python
get_travel_recommendation(location: str, date: str)
```

Provides a derived weather recommendation instead of simply returning raw API data.

Example question:

```text
Should I bring a jacket or umbrella to Seattle tomorrow?
```

The tool applies deterministic rules to the forecast.

Current recommendation rules include:

| Weather condition                | Recommendation                                |
| -------------------------------- | --------------------------------------------- |
| Precipitation probability >= 40% | Bring an umbrella                             |
| Forecast high < 60°F             | Bring a jacket                                |
| Wind > 25 mph                    | Warn about windy conditions                   |
| Forecast high >= 85°F            | Recommend hydration / hot-weather preparation |

If none of the thresholds are crossed, the tool explains that no special weather gear is recommended.

This tool demonstrates simple prediction/recommendation logic instead of acting as a direct API passthrough.

---

# Error Handling

The project handles failures at both the broker and MCP layers.

Examples include:

* Invalid or unresolved locations
* Open-Meteo request failures
* Invalid forecast dates
* External API outages
* Unexpected response data

Instead of exposing a Python stack trace to the agent, MCP tools return a clean error response.

The Supervisor Agent is also instructed not to invent weather information when a tool fails.

---

# Databricks Deployment

## MCP Server App

The FastMCP server is deployed as its own **Databricks App**.

The application uses `app.yaml` to start:

```text
weather_mcp_server.py
```

The server listens using HTTP transport and exposes its MCP endpoint at:

```text
/mcp
```

The MCP server was verified to start successfully using FastMCP and Streamable HTTP.

---

# Unity AI Gateway

After deploying the MCP server, it was registered in:

```text
Unity AI Gateway
    -> MCPs
    -> mcp-weather-prediction
```

The registered MCP service points to the deployed Databricks App's `/mcp` endpoint.

This allows Databricks agents to discover and execute the custom weather tools.

---

# Databricks Agent Bricks

A **Supervisor Agent** was created in Databricks and connected to:

```text
mcp-weather-prediction
```

as a UC MCP Service.

The Supervisor Agent can therefore translate natural-language weather questions into MCP tool calls.

For example:

```text
User:
What's the weather in Chicago right now?

        ↓

Supervisor Agent

        ↓

get_current_weather

        ↓

mcp-weather-prediction

        ↓

Open-Meteo

        ↓

Final natural-language response
```

---

# Agent System Prompt

The Supervisor Agent uses instructions designed to prevent weather hallucinations and encourage correct tool selection.

```text
You are a weather assistant.

Use the connected weather MCP tools whenever the user asks about current
or future weather.

Use get_current_weather for current conditions.

Use get_forecast for future weather questions.

Use get_travel_recommendation when the user asks what they should wear,
bring, or prepare for.

Do not invent temperatures, precipitation chances, wind speeds, or
conditions. Base weather claims only on MCP tool results.

If a location cannot be resolved, ask the user to clarify the location.

If a tool returns an error, explain the failure rather than guessing.

Treat forecasts as predictions, not guarantees.
```

A copy of these instructions is also stored in:

```text
system_prompt.md
```

---

# Agent Demonstrations

Three different natural-language questions were tested to demonstrate each required capability.

## Test 1 — Current Conditions

```text
What's the weather in Chicago right now?
```

The Supervisor Agent selected:

```text
get_current_weather
```

from:

```text
mcp-weather-prediction
```

Databricks displayed the MCP tool invocation, structured tool output, and final natural-language answer.

### Screenshot

```markdown
![Current Weather MCP Test](screenshots/current-weather.png)
```

---

## Test 2 — Weather Forecast

```text
Will it rain in Austin tomorrow?
```

The agent used:

```text
get_forecast
```

The forecast data was retrieved through the MCP server and interpreted by the Supervisor Agent.

### Screenshot

```markdown
![Forecast MCP Test](screenshots/forecast.png)
```

---

## Test 3 — Travel Recommendation

```text
Should I bring a jacket or umbrella to Seattle tomorrow?
```

The agent used:

```text
get_travel_recommendation
```

This demonstrates the project's derived prediction/recommendation capability.

### Screenshot

```markdown
![Travel Recommendation MCP Test](screenshots/recommendation.png)
```

---

# Optional Weather Dashboard

As an additional feature, the project includes a small Flask-based weather dashboard deployed as a **second Databricks App**.

The dashboard supports:

### Current Weather

Users can enter a location and view:

* Temperature
* Feels-like temperature
* Humidity
* Wind
* Weather code
* Last updated time

### Forecast

Users can select the forecast option and request multiple forecast days.

The dashboard displays:

* Daily high
* Daily low
* Precipitation probability
* Wind speed

### Travel Recommendation

Users can select a location and date to receive the same weather-based recommendation logic used by the MCP project.

Example dashboard output:

```text
Chicago, United States

Temperature     72.0°F
Feels Like      78.9°F
Humidity        91%
Wind            1.6 mph

Weather code: 3
Updated: 2026-08-09T21:30
```

The dashboard is intentionally deployed separately from the MCP server, following the multi-app architecture demonstrated in the Day 3 project.

---

# Local Testing

Install the MCP server dependencies:

```bash
pip install -r requirements.txt
```

Run the MCP server:

```bash
python weather_mcp_server.py
```

The server starts using FastMCP HTTP transport.

For example:

```text
Starting MCP server 'weather-prediction'
transport 'http'
http://0.0.0.0:8000/mcp
```

The broker can also be tested directly:

```python
from weather_broker import (
    get_current_weather,
    get_forecast,
    get_travel_recommendation,
)

print(get_current_weather("Chicago"))

print(get_forecast("Austin", 3))

print(
    get_travel_recommendation(
        "Seattle",
        "2026-08-11",
    )
)
```

---

# Running the Dashboard

Install the dashboard dependencies:

```bash
cd dashboard
pip install -r requirements.txt
```

Run:

```bash
python app.py
```

The Flask application starts on the configured Databricks application port or port `8000` when running locally.

---

# Databricks Apps

This project uses two separate Databricks Apps.

| Application              | Purpose                              |
| ------------------------ | ------------------------------------ |
| `mcp-weather-prediction` | Hosts the FastMCP weather server     |
| Weather Dashboard        | Optional user-facing Flask dashboard |

### MCP Server App

```text
<ADD YOUR MCP DATABRICKS APP URL HERE>
```

### Dashboard App

```text
<ADD YOUR DASHBOARD DATABRICKS APP URL HERE>
```

---

# Technologies Used

* Python
* FastMCP
* MCP / Model Context Protocol
* Open-Meteo
* Requests
* Flask
* Databricks Apps
* Databricks Agent Bricks
* Databricks Supervisor Agent
* Unity AI Gateway
* Git / GitHub

---

# Security

No weather API credentials are stored in the repository.

Open-Meteo does not require an API key, so there are:

* No hardcoded weather API keys
* No committed weather credentials
* No `.env` weather secrets
* No API credentials exposed through the MCP tools

If the project were changed to use an authenticated weather provider, API credentials should be stored using Databricks Secrets rather than committed to source control.

---

# Key Design Decisions

### Separate broker and MCP layers

HTTP requests and parsing are isolated in `weather_broker.py`, keeping the MCP tool functions thin.

### Deterministic recommendation logic

The recommendation tool applies explicit weather thresholds, making its behavior easy to understand and test.

### Tool-grounded agent responses

The Supervisor Agent is instructed to use MCP results for weather claims instead of generating weather values itself.

### Open-Meteo

Open-Meteo allows the entire pipeline to run without API-key management while still providing real weather data.

### Separate dashboard deployment

The optional dashboard runs as a separate Databricks App so the user-facing interface remains independent from the MCP protocol server.

---

# Future Improvements

Possible extensions include:

* Severe weather alerts
* National Weather Service integration
* Historical weather lookup
* Comparing weather between multiple cities
* Weather-code-to-description/icon mapping
* Query history and analytics
* Lakebase storage for recent agent predictions
* Dashboard charts
* Celsius/Fahrenheit selection
* More advanced packing recommendations

---

# Summary

This project demonstrates an end-to-end custom MCP workflow on Databricks:

```text
Natural-language question
        ↓
Databricks Supervisor Agent
        ↓
Unity AI Gateway
        ↓
Custom FastMCP Server
        ↓
Weather Broker
        ↓
Open-Meteo
        ↓
Structured weather data
        ↓
Agent response / recommendation
```

The completed system demonstrates all three required capabilities:

* **Current weather conditions**
* **Multi-day weather forecasts**
* **Derived weather-based recommendations**

It also includes an optional Flask weather dashboard deployed as a second Databricks App.
