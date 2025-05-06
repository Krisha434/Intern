import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import plotly.graph_objects as go

# Constants
PARAM_CITY = "q"
PARAM_API_KEY = "appid"
PARAM_UNITS = "units"
DEFAULT_UNITS = "metric"
DEFAULT_TIMEOUT = 10
DEFAULT_HISTORY_FILE = "history.json"
DEFAULT_GRAPH_OUTPUT = "graph.html"
DEFAULT_TEMPLATE = "plotly_white"
DEFAULT_LINE_COLOR = "blue"
DEFAULT_FORECAST_INTERVALS = 8

load_dotenv()

class WeatherDashboard:
    def __init__(self, config_file="configs.json"):
        self.config = self.load_config(config_file)
        self.api_key = self.config.get("api_key") or os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError("API key not found in config.json or environment variables")

        self.weather_url = self.config.get("weather_api_url")
        self.forecast_url = self.config.get("forecast_api_url")
        self.history_file = self.config.get("history_file", DEFAULT_HISTORY_FILE)
        self.units = self.config.get("units", DEFAULT_UNITS)
        self.timeout = self.config.get("timeout", DEFAULT_TIMEOUT)
        self.graph_output = self.config.get("graph_output", DEFAULT_GRAPH_OUTPUT)
        self.graph_settings = self.config.get("graph_settings", {})

    def load_config(self, config_file):
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {config_file} not found, using defaults")
            return {}
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in {config_file}")

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Warning: Could not parse history, starting fresh")
        return []

    def fetch_weather(self, city):
        try:
            params = {
                PARAM_CITY: city,
                PARAM_API_KEY: self.api_key,
                PARAM_UNITS: self.units
            }
            response = requests.get(self.weather_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error: {e}")

    def fetch_forecast(self, city):
        try:
            params = {
                PARAM_CITY: city,
                PARAM_API_KEY: self.api_key,
                PARAM_UNITS: self.units
            }
            response = requests.get(self.forecast_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to fetch forecast: {e}")

    def display_weather(self, weather_data):
        try:
            city = weather_data.get("name", "Unknown")
            temp = weather_data.get("main", {}).get("temp", "N/A")
            condition = weather_data.get("weather", [{}])[0].get("description", "N/A")
            humidity = weather_data.get("main", {}).get("humidity", "N/A")
            print(f"\nCurrent Weather in {city}")
            print(f"Temperature: {temp}°C")
            print(f"Condition: {condition}")
            print(f"Humidity: {humidity}%")
        except Exception as e:
            print(f"Error displaying weather: {e}")

    def display_forecast(self, forecast_data, hours):
        try:
            city = forecast_data.get("city", {}).get("name", "Unknown")
            print(f"\nForecast for {city} (next {hours * 3} hours):")
            for entry in forecast_data.get("list", [])[:hours]:
                timestamp = datetime.fromtimestamp(entry.get("dt")).strftime("%Y-%m-%d %H:%M")
                temp = entry.get("main", {}).get("temp", "N/A")
                condition = entry.get("weather", [{}])[0].get("description", "N/A")
                print(f"{timestamp}: {temp}°C, {condition}")
        except Exception as e:
            print(f"Error displaying forecast: {e}")

    def generate_graph(self, forecast_data):
        try:
            timestamps = []
            temperatures = []
            for entry in forecast_data.get("list", [])[:self.graph_settings.get("max_intervals", DEFAULT_FORECAST_INTERVALS)]:
                timestamps.append(datetime.fromtimestamp(entry.get("dt")).strftime("%Y-%m-%d %H:%M"))
                temperatures.append(entry.get("main", {}).get("temp", 0))

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=temperatures,
                mode="lines+markers",
                name="Temperature",
                line=dict(color=self.graph_settings.get("line_color", DEFAULT_LINE_COLOR))
            ))

            fig.update_layout(
                title="Forecast Temperature",
                xaxis_title="Time",
                yaxis_title=f"Temp (°{self.units.upper()})",
                template=self.graph_settings.get("template", DEFAULT_TEMPLATE)
            )

            # Save as HTML only
            fig.write_html(self.graph_output)
            print(f"Graph saved to {self.graph_output}")
        except Exception as e:
            print(f"Failed to generate graph: {e}")

    def save_history(self, city, weather, forecast, hours):
        history = self.load_history()
        try:
            entry = {
                "city": city,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "current_weather": {
                    "temperature": weather.get("main", {}).get("temp", "N/A"),
                    "condition": weather.get("weather", [{}])[0].get("description", "N/A"),
                    "humidity": weather.get("main", {}).get("humidity", "N/A")
                },
                "forecast": [
                    {
                        "timestamp": datetime.fromtimestamp(entry.get("dt")).strftime("%Y-%m-%d %H:%M"),
                        "temperature": entry.get("main", {}).get("temp", "N/A"),
                        "condition": entry.get("weather", [{}])[0].get("description", "N/A")
                    }
                    for entry in forecast.get("list", [])[:hours]
                ]
            }
            history.append(entry)
            with open(self.history_file, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def run(self):
        try:
            city = input("Enter city name: ").strip()
            hours_input = input("Enter number of 3-hour forecast intervals (1–40): ").strip()
            hours = int(hours_input) if hours_input.isdigit() and 1 <= int(hours_input) <= 40 else DEFAULT_FORECAST_INTERVALS

            weather = self.fetch_weather(city)
            forecast = self.fetch_forecast(city)
            self.display_weather(weather)
            self.display_forecast(forecast, hours)
            self.generate_graph(forecast)
            self.save_history(city, weather, forecast, hours)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    WeatherDashboard().run()