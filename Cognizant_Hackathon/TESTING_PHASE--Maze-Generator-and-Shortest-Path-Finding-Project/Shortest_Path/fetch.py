import requests
import datetime

class Api_Data:
    def __init__(self, coordinate):
        self.co = coordinate
        self.api_key = '0794673555559a129540662e3029b866'  # Replace with your OpenWeather API key

    def air_index(self):
        try:
            ENDPOINT = 'https://api.openweathermap.org/data/2.5/air_pollution'
            parameters = {
                'lat': self.co[0],
                'lon': self.co[1],
                'appid': self.api_key,
            }
            response = requests.get(ENDPOINT, params=parameters)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()
            if data['list']:
                air_quality = data['list'][0]['main']
                aqi = air_quality['aqi']
                aqi_units = 'dimensionless'  # AQI does not have a traditional unit, it's a scale
                return f'The air quality index (AQI) is {aqi} ({aqi_units})'
            return 'No air quality data available.'
        except requests.HTTPError as http_err:
            return f'HTTP error occurred: {str(http_err)}'
        except Exception as e:
            return f'Error fetching air index: {str(e)}'

    def is_holiday(self):
        try:
            year = datetime.datetime.now().year
            ENDPOINT = 'https://calendarific.com/api/v2/holidays'
            parameters = {
                'api_key': 'Rx82VgQMnyEBMUvs9OKyl4jMVt879uFx',  # Replace with your Calendarific API key
                'country': 'IN',
                'year': year,
            }
            response = requests.get(ENDPOINT, params=parameters)
            response.raise_for_status()
            holidays = response.json().get('response', {}).get('holidays', [])
            
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            print(f"Today's date: {today}")  # Debug print

            for holiday in holidays:
                holiday_date = holiday.get('date', {}).get('iso', '')
                print(f"Holiday date: {holiday_date}")  # Debug print
                if holiday_date == today:
                    return 'Holiday'
            return 'Not a holiday'
        except requests.HTTPError as http_err:
            return f'HTTP error occurred: {str(http_err)}'
        except Exception as e:
            return f'Error checking holidays: {str(e)}'

    def is_weekend(self):
        try:
            today = datetime.datetime.now().strftime('%A')
            if today in ['Saturday', 'Sunday']:
                return 'Weekend'
            return 'Not a weekend'
        except Exception as e:
            return f'Error checking weekend status: {str(e)}'

    def wind_direction(self):
        try:
            ENDPOINT = 'https://api.openweathermap.org/data/2.5/weather'
            parameters = {
                'lat': self.co[0],
                'lon': self.co[1],
                'appid': self.api_key,
            }
            response = requests.get(ENDPOINT, params=parameters)
            response.raise_for_status()
            wind_data = response.json().get('wind', {})
            wind_direction = wind_data.get('deg', None)
            if wind_direction is not None:
                directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                index = round(wind_direction / (360. / len(directions)))
                return directions[index % len(directions)]
            return 'Wind direction data not available.'
        except requests.HTTPError as http_err:
            return f'HTTP error occurred: {str(http_err)}'
        except Exception as e:
            return f'Error fetching wind direction: {str(e)}'

    def temperature(self):
        try:
            ENDPOINT = 'https://api.openweathermap.org/data/2.5/weather'
            parameters = {
                'lat': self.co[0],
                'lon': self.co[1],
                'appid': self.api_key,
                'units': 'metric',
            }
            response = requests.get(ENDPOINT, params=parameters)
            response.raise_for_status()
            temperature = response.json().get('main', {}).get('temp', None)
            if temperature is not None:
                return f'{temperature:.2f} °C'  # Ensure "°C" is appended only once and formatted to 2 decimal places
            return 'Temperature data not available.'
        except requests.HTTPError as http_err:
            return f'HTTP error occurred: {str(http_err)}'
        except Exception as e:
            return f'Error fetching temperature: {str(e)}'

    def humidity(self):
        try:
            ENDPOINT = 'https://api.openweathermap.org/data/2.5/weather'
            parameters = {
                'lat': self.co[0],
                'lon': self.co[1],
                'appid': self.api_key,
                'units': 'metric',
            }
            response = requests.get(ENDPOINT, params=parameters)
            response.raise_for_status()
            humidity = response.json().get('main', {}).get('humidity', None)
            if humidity is not None:
                return f'{humidity} %'
            return 'Humidity data not available.'
        except requests.HTTPError as http_err:
            return f'HTTP error occurred: {str(http_err)}'
        except Exception as e:
            return f'Error fetching humidity: {str(e)}'
