import pandas as pd
import os
import pyproj
import requests
import concurrent.futures
import argparse
from tqdm import tqdm

# Create a single transformer object to be reused
transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:31982", always_xy=True)

def convert_lat_lon_to_UTM(lat, lon):
    utm_x, utm_y = transformer.transform(lon, lat)
    UTM = f'POINT({utm_x} {utm_y})'
    return UTM

def duplicate_row_with_new_UTM(row, coordinates):
    new_row = row._asdict()
    new_row['the_geom'] = convert_lat_lon_to_UTM(coordinates[1], coordinates[0])
    return new_row

def normalize_google_response(data):
    """Convert Google API response format to match Geoapify format"""
    if not data or 'results' not in data or not data['results']:
        return None

    normalized_data = {
        'features': []
    }

    for result in data['results']:
        if 'geometry' in result and 'location' in result['geometry']:
            location = result['geometry']['location']
            feature = {
                'geometry': {
                    'coordinates': [location['lng'], location['lat']]
                }
            }
            normalized_data['features'].append(feature)

    return normalized_data

def fetch_geocode(endereco, api_type='geoapify'):
    """Fetch geocode data from specified API

    Args:
        endereco: Address to geocode
        api_type: 'geoapify' or 'google'
    """
    try:
        if api_type.lower() == 'google':
            url = f'http://localhost:8080/external/geocode?address={endereco}'
        else:  # default to geoapify
            url = f'http://localhost:8080/external/geocode-geoapify?address={endereco}'

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Normalize Google response to match Geoapify format
            if api_type.lower() == 'google':
                return normalize_google_response(data)
            return data
        return None
    except Exception as e:
        print(f"Error fetching geocode for {endereco}: {e}")
        return None

# Set up argument parser
parser = argparse.ArgumentParser(description='Geocode addresses using different APIs')
parser.add_argument('--api', choices=['geoapify', 'google'], default='geoapify',
                    help='API to use for geocoding (default: geoapify)')
parser.add_argument('--input', default='input/Honório_Serpa_teste_api_pontos.csv',
                    help='Input CSV file path (default: input/Honório_Serpa_teste_api_pontos.csv)')
args = parser.parse_args()

# Get input filename and API type from arguments
input_filename = args.input
api_type = args.api

print(f"Using {api_type} API for geocoding")
df = pd.read_csv(input_filename, sep=';')

# Prepare data for processing
rows_to_process = []
for row_idx, row in enumerate(df.itertuples()):
    if pd.isna(row.the_geom):
        endereco = row.endereco.replace('-', '').replace('P/', '') + ' PARANA'
        rows_to_process.append((row_idx, row, endereco))

# Process data in parallel
new_rows = []
updates = {}

print(f"Processing {len(rows_to_process)} addresses using {api_type} API...")
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    # Map the fetch_geocode function to all addresses with the selected API type
    future_to_row = {executor.submit(fetch_geocode, row[2], api_type): row for row in rows_to_process}

    # Process results as they complete
    for future in tqdm(concurrent.futures.as_completed(future_to_row), total=len(rows_to_process)):
        row_idx, row, endereco = future_to_row[future]
        try:
            data = future.result()
            if data:
                for i, feature in enumerate(data.get('features', [])):
                    coordinates = feature.get('geometry').get('coordinates')
                    if i == 0:
                        updates[row_idx] = convert_lat_lon_to_UTM(coordinates[1], coordinates[0])
                    else:
                        new_rows.append(duplicate_row_with_new_UTM(row, coordinates))
        except Exception as e:
            print(f"Error processing {endereco}: {e}")

# Apply updates to the dataframe
for row_idx, utm in updates.items():
    df.at[row_idx, 'the_geom'] = utm

# Add all new rows at once if there are any
if new_rows:
    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)


output_dir = 'output'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

input_filepath = os.path.basename(input_filename + f'-{api_type}.csv')
output_path = os.path.join(output_dir, input_filepath)
df.to_csv(output_path, sep=';', index=False)
