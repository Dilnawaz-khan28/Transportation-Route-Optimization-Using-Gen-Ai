import requests
import traceback
from flask import Flask, render_template, request, jsonify
import folium
from folium.plugins import HeatMap
import openrouteservice
from traffic_volume_prediction import predict_traffic
from fetch import Api_Data
from Algorithm import Dijkstra, A_search, BFS, Q_Learning
import math
import logging

app = Flask(__name__, template_folder='templates')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Replace with your actual API keys and model IDs
COHERE_API_KEY = 'HnJmUL8THGonm9ew17Eqz2KAPyQ3ef6DSLXHWawD'
COHERE_API_URL = 'https://api.cohere.com/v1/generate'
MODEL_ID = 'command'  # Ensure this is the correct model ID

def geocode_place(place_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={place_name}&addressdetails=1"
        headers = {'User-Agent': 'YourAppName/1.0 (your.email@example.com)'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
        logger.error(f"Geocoding failed for place: {place_name}")
        return None, None
    except requests.RequestException as e:
        logger.error(f"Error during geocoding: {e}")
        return None, None

def reverse_geocode(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1"
        headers = {'User-Agent': 'YourAppName/1.0 (your.email@example.com)'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'address' in data:
            address = data['address']
            return f"{address.get('road', 'Unknown')}, {address.get('city', 'Unknown')}, {address.get('country', 'Unknown')}"
        return "Unknown Location"
    except requests.RequestException as e:
        logger.error(f"Error during reverse geocoding: {e}")
        return "Error in location"

def fetch_real_time_traffic_data(lat1, lng1, lat2, lng2):
    try:
        url = f"https://data.traffic.hereapi.com/v7/flow?locationReferencing=shape&in=bbox:{lng1},{lat1},{lng2},{lat2}&apiKey=ZhY92oQpAlyZoyMaBp9mI3vFedz_kR9mq0H3M3HhEZY"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching traffic data: {e}")
        return {}

def fetch_pois_along_route(lat1, lng1, lat2, lng2, poi_type):
    pois_with_address = []
    try:
        overpass_url = "http://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (
          node["amenity"="{poi_type}"](around:1000, {lat1}, {lng1});
          node["amenity"="{poi_type}"](around:1000, {lat2}, {lng2});
        );
        out;
        """
        response = requests.get(overpass_url, params={'data': query})
        response.raise_for_status()
        data = response.json()

        for poi in data.get('elements', []):
            name = poi.get('tags', {}).get('name', 'Unnamed')
            lat = poi['lat']
            lon = poi['lon']
            address = reverse_geocode(lat, lon)  # Get address for each POI
            pois_with_address.append({'name': name, 'lat': lat, 'lon': lon, 'address': address})

    except requests.RequestException as e:
        logger.error(f"Error fetching POIs: {e}")

    return pois_with_address

def format_duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

def generate_text(prompt):
    try:
        headers = {
            'Authorization': f'Bearer {COHERE_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': MODEL_ID,
            'prompt': prompt,
            'max_tokens': 150
        }
        response = requests.post(COHERE_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()
        return response_json['generations'][0]['text'].strip()
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        return "Error generating text due to HTTP issue."
    except Exception as e:
        logger.error(f"Error generating text: {e}")
        logger.debug(traceback.format_exc())
        return "Error generating text due to an unexpected issue."

def haversine(lat1, lon1, lat2, lon2):
    # Radius of Earth in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distance in kilometers
    distance = R * c
    return distance

@app.route('/', methods=['POST', 'GET'])
def get_map():
    map_html = None
    formatted_duration = ""
    air_index = None
    holiday_status = None
    weekend_status = None
    wind_direction = None
    temperature = None
    humidity = None
    generated_text = None
    predicted_traffic_volume = None
    places_of_interest = None
    start_location_name = ""
    end_location_name = ""

    if request.method == 'POST':
        try:
            start_place = request.form['start_place']
            end_place = request.form['end_place']
            vehicle_type = request.form['vehicle_type']
            poi_type = request.form.get('poi_type', 'none')
            prompt = request.form.get('prompt')

            lat1, lng1 = geocode_place(start_place)
            lat2, lng2 = geocode_place(end_place)

            if lat1 is None or lat2 is None:
                raise ValueError("Geocoding failed for one or both place names.")

            start_location_name = reverse_geocode(lat1, lng1)
            end_location_name = reverse_geocode(lat2, lng2)

            traffic_data = fetch_real_time_traffic_data(lat1, lng1, lat2, lng2)
            coordinates = [(point['lat'], point['lng']) for result in traffic_data.get('results', []) for link in result.get('location', {}).get('shape', {}).get('links', []) for point in link.get('points', [])]

            m = folium.Map(location=[(lat1 + lat2) / 2, (lng1 + lng2) / 2], zoom_start=14)
            HeatMap(coordinates).add_to(m)

            client = openrouteservice.Client(key='5b3ce3597851110001cf6248ad4150d949ba4b0ebd86565a37e79cde')
            coords = [[lng1, lat1], [lng2, lat2]]
            profile = 'driving-car' if vehicle_type == 'car' else 'cycling-regular' if vehicle_type == 'bicycle' else 'foot-walking'
            route = client.directions(coordinates=coords, profile=profile, format='geojson')
            duration = route['features'][0]['properties']['segments'][0]['duration']

            folium.GeoJson(route, name='Shortest Path').add_to(m)
            folium.Marker([lat1, lng1], popup=f'Start: {start_location_name}', icon=folium.Icon(color='green', icon='play')).add_to(m)
            folium.Marker([lat2, lng2], popup=f'End: {end_location_name}', icon=folium.Icon(color='red', icon='stop')).add_to(m)

            map_html = m._repr_html_()
            formatted_duration = format_duration(duration)

            predicted_traffic_volume = predict_traffic(lat1, lng1, lat2, lng2)

            api_data = Api_Data((lat1, lng1))
            air_index = api_data.air_index()
            holiday_status = api_data.is_holiday()
            weekend_status = api_data.is_weekend()
            wind_direction = api_data.wind_direction()
            temperature = api_data.temperature()
            humidity = api_data.humidity()

            if poi_type != 'none':
                places_of_interest = fetch_pois_along_route(lat1, lng1, lat2, lng2, poi_type)

                if prompt:
                    # Generate prompt for Cohere
                    poi_data = [f"POI Name: {poi['name']}, Distance from Start: {haversine(lat1, lng1, poi['lat'], poi['lon']):.2f} km, Distance from End: {haversine(lat2, lng2, poi['lat'], poi['lon']):.2f} km" for poi in places_of_interest]
                    poi_list_str = "\n".join(poi_data)
                    ai_prompt = f"From the following list of points of interest, which one is closest to both the starting point and the ending point?\n{poi_list_str}\n\nPrompt: {prompt}"
                    generated_text = generate_text(ai_prompt)

        except ValueError as e:
            logger.error(f"Value error: {e}")
            generated_text = "Error: " + str(e)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.debug(traceback.format_exc())
            generated_text = "Error generating text."

    return render_template('index.html', map_html=map_html, duration=formatted_duration,
                           air_index=air_index, holiday_status=holiday_status,
                           weekend_status=weekend_status, wind_direction=wind_direction,
                           temperature=temperature, humidity=humidity, generated_text=generated_text,
                           predicted_traffic_volume=predicted_traffic_volume, 
                           places_of_interest=places_of_interest if places_of_interest else [],
                           start_location_name=start_location_name,
                           end_location_name=end_location_name)

@app.route('/find_route', methods=['POST'])
def find_route():
    try:
        start_place = request.form['start_place']
        end_place = request.form['end_place']

        lat1, lng1 = geocode_place(start_place)
        lat2, lng2 = geocode_place(end_place)

        if lat1 is None or lat2 is None:
            raise ValueError("Geocoding failed for one or both place names.")

        graph = {}  # Replace with actual graph data

        dijkstra = Dijkstra(graph, (lat1, lng1), (lat2, lng2))
        a_star = A_search(graph, (lat1, lng1), (lat2, lng2))
        bfs = BFS(graph, (lat1, lng1), (lat2, lng2))
        
        dijkstra_route = dijkstra.compute_route()
        a_star_route = a_star.compute_route()
        bfs_route = bfs.compute_route()
        
        return jsonify({
            "dijkstra": dijkstra_route,
            "a_star": a_star_route,
            "bfs": bfs_route
        })
    except ValueError as e:
        logger.error(f"Value error: {e}")
        return jsonify({"error": f"Geocoding error: {e}"})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(traceback.format_exc())
        return jsonify({"error": "Failed to find route"})

@app.route('/optimize_traffic', methods=['POST'])
def optimize_traffic():
    try:
        start_place = request.form['start_place']
        end_place = request.form['end_place']

        lat1, lng1 = geocode_place(start_place)
        lat2, lng2 = geocode_place(end_place)

        if lat1 is None or lat2 is None:
            raise ValueError("Geocoding failed for one or both place names.")

        predicted_traffic_volume = predict_traffic(lat1, lng1, lat2, lng2)
        return jsonify({"predicted_traffic_volume": predicted_traffic_volume})
    except ValueError as e:
        logger.error(f"Value error: {e}")
        return jsonify({"error": f"Geocoding error: {e}"})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(traceback.format_exc())
        return jsonify({"error": "Failed to optimize traffic"})

if __name__ == '__main__':
    app.run(debug=True)
