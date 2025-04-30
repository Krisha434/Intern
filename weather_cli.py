import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv 
# Load environment variables from .env file
load_dotenv()  

class WeatherDashboard:
    def __init__(self):
        """Initialize the WeatherDashboard with API key and configuration."""
        # Import the variable 'api_key' from the .env file
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError("api_key not found in .env file")
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
        self.history_file = "history.json"

    def load_history(self):
        """Load historical queries from JSON file."""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return []

    def save_history(self, city, timestamp, weather_data, forecast_data):
        """Save a query including city, timestamp, and weather details to the history file."""
        history = self.load_history()
        try:
            # Validate and extract current weather details
            if not weather_data or 'main' not in weather_data or 'weather' not in weather_data:
                current_weather = {}
            else:
                current_weather = {
                    "temperature": weather_data['main']['temp'],
                    "condition": weather_data['weather'][0]['description'],
                    "humidity": weather_data['main']['humidity']
                }

            # Validate and extract forecast details
            if not forecast_data or 'list' not in forecast_data:
                forecast = []
            else:
                forecast = [
                    {
                        "timestamp": datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d %H:%M'),
                        "temperature": item['main']['temp'],
                        "condition": item['weather'][0]['description']
                    }
                    for item in forecast_data['list']
                ]

            # Save the complete entry
            history.append({
                "city": city,
                "timestamp": timestamp,
                "current_weather": current_weather,
                "forecast": forecast
            })

            # Write to history.json
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=4)

        except Exception as e:
            print(f"Error saving to history: {e}")

    def fetch_weather(self, city):
        """Fetch current weather data from OpenWeatherMap API using requests.get."""
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return None

    def fetch_forecast(self, city):
        """Fetch weather forecast data from OpenWeatherMap API using requests.get."""
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }
        try:
            response = requests.get(self.forecast_url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return None

    def display_weather(self, data):
        """Display formatted current weather conditions."""
        if not data or 'main' not in data:
            print("No weather data available.")
            return
        temp = data['main']['temp']
        description = data['weather'][0]['description']
        humidity = data['main']['humidity']
        print(f"\nCurrent Weather for {data['name']}:")
        print(f"Temperature: {temp}°C")
        print(f"Condition: {description}")
        print(f"Humidity: {humidity}%")

    def display_forecast(self, data, num_entries):
        """Display formatted forecast data for the specified number of entries."""
        if not data or 'list' not in data:
            print("No forecast data available.")
            return
        print(f"\n3-Hour Forecast for {data['city']['name']}:")
        # Limit the number of forecast entries to display based on user input
        for item in data['list'][:num_entries]:
            timestamp = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d %H:%M')
            temp = item['main']['temp']
            description = item['weather'][0]['description']
            print(f"{timestamp}: {temp}°C, {description}")

    def run(self):
        """Run the weather dashboard with user input for city and forecast entries."""
        try:
            # Get city name from user input
            city = input("Enter the city name: ").strip()
            if not city:
                print("City name cannot be empty.")
                return

            # Get number of forecast entries from user input
            while True:
                try:
                    num_entries = int(input("Enter the number of forecast entries to display (1-40): ").strip())
                    if 1 <= num_entries <= 40:  # OpenWeatherMap forecast API returns up to 40 entries (5 days, 3-hour intervals)
                        break
                    else:
                        print("Please enter a number between 1 and 40.")
                except ValueError:
                    print("Please enter a valid number.")

            # Fetch and display current weather
            weather_data = self.fetch_weather(city)
            if weather_data:
                self.display_weather(weather_data)
            else:
                print("Unable to fetch current weather data.")

            # Fetch and display forecast
            forecast_data = self.fetch_forecast(city)
            if forecast_data:
                self.display_forecast(forecast_data, num_entries)
            else:
                print("Unable to fetch forecast data.")

            # Save to history with weather details
            if weather_data or forecast_data:  # Save even if one is available
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_history(city, timestamp, weather_data or {}, forecast_data or {})
                print(f"\nQuery saved to {self.history_file}")
            else:
                print("No data to save to history.")

        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main function to run the WeatherDashboard."""
    weather_dashboard = WeatherDashboard()
    weather_dashboard.run()

if __name__ == "__main__":
    main()