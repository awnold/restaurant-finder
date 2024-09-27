from flask import Flask, render_template, request, make_response
import pandas as pd
import requests
from io import StringIO

app = Flask(__name__)

# Convert ZIP code to latitude and longitude with Zippopotam.us API
def get_lat_lon_from_zip(zip_code):
    zippopotam_url = f"http://api.zippopotam.us/us/{zip_code}"
    response = requests.get(zippopotam_url)
    
    if response.status_code == 200:
        data = response.json()
        lat = data['places'][0]['latitude']
        lon = data['places'][0]['longitude']
        return lat, lon
    else:
        print(f"Error: Unable to fetch data for ZIP code {zip_code}. Status Code: {response.status_code}")
        return None, None

# Get restaurants based on latitude, longitude, and radius with OpenStreetMap API
def get_restaurants_by_lat_long(lat, lon, radius=1000):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    node
      ["amenity"="restaurant"]
      (around:{radius},{lat},{lon});
    out;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    
    restaurant_data = []
    for element in data['elements']:
        name = element.get('tags', {}).get('name', 'Unknown')
        address = element.get('tags', {}).get('addr:street', '') + ' ' + element.get('tags', {}).get('addr:housenumber', '')
        website = element.get('tags', {}).get('website', '')
        phone_number = element.get('tags', {}).get('phone', '')
        
        # Filter out restaurants with no address
        if address.strip():
            restaurant_data.append({
                'Name': name,
                'Website': website,
                'Phone Number': phone_number,
                'Address': address
            })
    
    return restaurant_data

@app.route("/", methods=["GET", "POST"])
def index():
    error_message = None
    results = None
    result_count = 0
    zip_code = '' 
    radius = ''

    if request.method == "POST":
        zip_code = request.form.get("zip_code")
        radius = request.form.get("radius")

        # Max radius of 25000
        if float(radius) > 25000:
            error_message = "Radius cannot exceed 25,000 meters."
        else:
            # Convert ZIP code to latitude and longitude
            lat, lon = get_lat_lon_from_zip(zip_code)
            if lat and lon:
                # Get restaurant data
                results = get_restaurants_by_lat_long(lat, lon, radius)
                result_count = len(results)  # Count the number of results
            else:
                error_message = "Invalid ZIP code. Please try again."

    return render_template("index.html", results=results, result_count=result_count, zip_code=zip_code, radius=radius, error_message=error_message)

# Route to download CSV file
@app.route("/download_csv")
def download_csv():
    zip_code = request.args.get('zip_code', '')
    radius = request.args.get('radius', '')
    lat, lon = get_lat_lon_from_zip(zip_code)
    results = get_restaurants_by_lat_long(lat, lon, radius)

    # Create a CSV file from the results
    df = pd.DataFrame(results)
    csv_data = StringIO()
    df.to_csv(csv_data, index=False)
    csv_data.seek(0)

    # Create the response object to send the CSV file
    response = make_response(csv_data.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=restaurants_{zip_code}_{radius}.csv"
    response.headers["Content-Type"] = "text/csv"

    return response

if __name__ == "__main__":
    app.run(debug=True)
