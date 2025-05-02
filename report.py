import requests
import json
import os
from datetime import datetime
import plotly.graph_objects as go

class WeatherDashboard:
    def __init__(self, config_file="configs.json"):
        self.config = self.load_config(config_file)
        self.api_key = self.config.get("api_key") or os.environ.get("api_key")
        if not self.api_key:
            raise ValueError("API key not found in config.json or environment variables")
        self.weather_url = self.config.get("weather_api_url")
        self.forecast_url = self.config.get("forecast_api_url")
        self.history_file = self.config.get("history_file", "history.json")
        self.units = self.config.get("units", "metric")
        self.timeout = self.config.get("timeout", 10)
        self.graph_output = self.config.get("graph_output", "graph.html")
        self.graph_settings = self.config.get("graph_settings", {})

    def load_config(self, config_file):
        """Load configuration from config.json."""
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file {config_file} not found")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in {config_file}")

    def load_history(self):
        """Load history from history.json."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in {self.history_file}, starting with empty history")
                return []
        return []

    def fetch_weather(self, city):
        """Fetch current weather data for a city."""
        try:
            params = {"q": city, "appid": self.api_key, "units": self.units}
            response = requests.get(self.weather_url, params=params, timeout=self.timeout)
            if response.status_code == 404:
                raise ValueError("City not found")
            response.raise_for_status()
            data = response.json()
            if not data.get("main") or not data.get("weather"):
                raise KeyError("Incomplete weather data")
            return data
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to fetch weather data: {e}")

    def fetch_forecast(self, city):
        """Fetch forecast data for a city."""
        try:
            params = {"q": city, "appid": self.api_key, "units": self.units}
            response = requests.get(self.forecast_url, params=params, timeout=self.timeout)
            if response.status_code == 404:
                raise ValueError("City not found")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to fetch forecast data: {e}")

    def display_weather(self, weather_data):
        """Display current weather data."""
        city = weather_data.get("name", "Unknown")
        temp = weather_data.get("main", {}).get("temp", "Not available")
        condition = weather_data.get("weather", [{}])[0].get("description", "Not available")
        humidity = weather_data.get("main", {}).get("humidity", "Not available")
        print(f"Current Weather for {city}")
        print(f"Temperature: {temp}°C")
        print(f"Condition: {condition}")
        print(f"Humidity: {humidity}%")

    def display_forecast(self, forecast_data, hours):
        """Display forecast data for the specified number of intervals."""
        city = forecast_data.get("city", {}).get("name", "Unknown")
        print(f"3-Hour Forecast for {city}")
        for entry in forecast_data.get("list", [])[:hours]:
            timestamp = datetime.fromtimestamp(entry.get("dt")).strftime("%Y-%m-%d %H:%M")
            temp = entry.get("main", {}).get("temp", "Not available")
            condition = entry.get("weather", [{}])[0].get("description", "Not available")
            print(f"{timestamp}: {temp}°C, {condition}")

    def generate_graph(self, forecast_data):
        """Generate an HTML file with a temperature forecast graph."""
        try:
            timestamps = []
            temperatures = []
            city = forecast_data.get("city", {}).get("name", "Unknown")
            max_intervals = self.graph_settings.get("max_intervals", 8)  # Default to 24 hours

            for entry in forecast_data.get("list", [])[:max_intervals]:
                timestamps.append(datetime.fromtimestamp(entry.get("dt")).strftime("%Y-%m-%d %H:%M"))
                temperatures.append(entry.get("main", {}).get("temp", 0))

            # Create Plotly line graph
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=temperatures,
                mode="lines+markers",
                name="Temperature",
                line=dict(color=self.graph_settings.get("line_color", "blue"))
            ))

            fig.update_layout(
                title=f"Temperature Forecast for {city}",
                xaxis_title="Time",
                yaxis_title=f"Temperature (°{self.units.capitalize()})",
                template=self.graph_settings.get("template", "plotly_white")
            )

            # Save to HTML
            fig.write_html(self.graph_output, auto_open=False)
            return self.graph_output
        except Exception as e:
            print(f"Error generating graph: {e}")
            return None

    def run(self):
        """Run the weather dashboard CLI."""
        try:
            city = input("Enter city name: ").strip()
            if not city:
                raise ValueError("City name cannot be empty")
            hours = input("Enter number of 3-hour forecast intervals (e.g., 2 for 6 hours): ").strip()
            hours = int(hours) if hours.isdigit() else 2  # Default to 2 if invalid
            weather = self.fetch_weather(city)
            forecast = self.fetch_forecast(city)
            self.display_weather(weather)
            self.display_forecast(forecast, hours)
            graph_file = self.generate_graph(forecast)
            history_entry = {
                "city": city,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "current_weather": {
                    "temperature": weather.get("main", {}).get("temp"),
                    "condition": weather.get("weather", [{}])[0].get("description"),
                    "humidity": weather.get("main", {}).get("humidity")
                },
                "forecast": [
                    {
                        "timestamp": datetime.fromtimestamp(entry.get("dt")).strftime("%Y-%m-%d %H:%M"),
                        "temperature": entry.get("main", {}).get("temp"),
                        "condition": entry.get("weather", [{}])[0].get("description")
                    } for entry in forecast.get("list", [])[:hours]
                ]
            }
            history = self.load_history()
            history.append(history_entry)
            with open(self.history_file, "w") as f:
                json.dump(history, f, indent=2)
            print(f"Query saved to {self.history_file}")
            if graph_file:
                print(f"Graphical report saved to {graph_file}")
        except ValueError as e:
            print(f"Error: {e}")
        except RuntimeError as e:
            print(f"API Error: {e}")
        except KeyError as e:
            print(f"Data Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    dashboard = WeatherDashboard()
    dashboard.run()