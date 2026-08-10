import os
from flask import Flask, render_template, request
import weather_broker

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    location = ""
    action = "current"
    days = 3
    date = ""

    if request.method == "POST":
        location = request.form.get("location", "").strip()
        action = request.form.get("action", "current")
        days = int(request.form.get("days", 3))
        date = request.form.get("date", "").strip()

        try:
            if not location:
                raise ValueError("Please enter a location.")
            if action == "current":
                result = weather_broker.get_current_weather(location)
            elif action == "forecast":
                result = weather_broker.get_forecast(location, days)
            elif action == "recommendation":
                if not date:
                    raise ValueError(
                        "Please select a date for the recommendation."
                    )

                result = weather_broker.get_travel_recommendation(
                    location,
                    date,
                )

        except Exception as exc:
            error = str(exc)

    return render_template(
        "index.html",
        result=result,
        error=error,
        location=location,
        action=action,
        days=days,
        date=date,
    )


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("DATABRICKS_APP_PORT",os.getenv("PORT", 8000),))
    app.run(host="0.0.0.0",port=port,)