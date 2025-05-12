"""
Geocoding Visualization Tool

This script generates an interactive HTML map from geocoded points in a CSV file.
It has been optimized for performance with large datasets using the following techniques:
1. Marker clustering - Groups nearby markers to reduce initial rendering load
2. FastMarkerCluster - Uses JavaScript for more efficient marker creation
3. Optional marker limiting - Can sample a subset of points for very large datasets

Usage:
  python see_geocoding.py [OPTIONS]

Options:
  --file=FILENAME    Specify the input CSV file (default: Campo_Mourão_teste_api_pontos.csv)
  --max=N            Limit the number of markers to N
  --no-fast          Use regular MarkerCluster instead of FastMarkerCluster
  --help, -h         Show this help message and exit
"""

import pandas as pd
import folium
from folium.plugins import MarkerCluster, FastMarkerCluster
from pyproj import Transformer
import numpy as np
import sys

# Parse command line arguments
max_markers = None
use_fast_markers = True
input_filename = 'Campo_Mourão_teste_api_pontos.csv'
show_help = False

if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
        if arg.startswith('--max='):
            try:
                max_markers = int(arg.split('=')[1])
            except ValueError:
                print(f"Invalid value for --max: {arg.split('=')[1]}")
        elif arg == '--no-fast':
            use_fast_markers = False
        elif arg.startswith('--file='):
            input_filename = arg.split('=')[1]
        elif arg in ['--help', '-h']:
            show_help = True

if show_help:
    print("Usage: python see_geocoding.py [OPTIONS]")
    print("Options:")
    print("  --file=FILENAME    Specify the input CSV file (default: Campo_Mourão_teste_api_pontos.csv)")
    print("  --max=N            Limit the number of markers to N")
    print("  --no-fast          Use regular MarkerCluster instead of FastMarkerCluster")
    print("  --help, -h         Show this help message and exit")
    sys.exit(0)

# Read the CSV file
df = pd.read_csv(f'output/{input_filename}', sep=';')

# Extract X and Y coordinates from the POINT string
df['x'] = df['the_geom'].str.extract(r'POINT\(([\d.]+)')
df['y'] = df['the_geom'].str.extract(r'([\d.]+)\)')

# Convert strings to float
df['x'] = df['x'].astype(float)
df['y'] = df['y'].astype(float)

# Create transformer from UTM zone 22S (EPSG:31982) to WGS84 (EPSG:4326)
transformer = Transformer.from_crs('EPSG:31982', 'EPSG:4326', always_xy=True)

# Convert coordinates
coords = [transformer.transform(x, y) for x, y in zip(df['x'], df['y'])]
df['longitude'] = [coord[0] for coord in coords]
df['latitude'] = [coord[1] for coord in coords]

# Filter out rows with NaN values in latitude or longitude
valid_df = df.dropna(subset=['latitude', 'longitude'])

# Limit the number of markers if specified
if max_markers is not None and len(valid_df) > max_markers:
    print(f"Limiting to {max_markers} markers out of {len(valid_df)} valid coordinates")
    valid_df = valid_df.sample(max_markers, random_state=42)

# Print summary of filtered data
print(f"Total rows: {len(df)}")
print(f"Valid coordinates: {len(valid_df)}")
print(f"Rows dropped due to missing coordinates: {len(df) - len(valid_df)}")
print(f"Using {'FastMarkerCluster' if use_fast_markers else 'MarkerCluster'} for better performance")

# Create a map centered on the mean coordinates of valid points
center_lat = valid_df['latitude'].mean()
center_lon = valid_df['longitude'].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=15)

if use_fast_markers:
    # Use FastMarkerCluster for better performance with large datasets
    # Create a callback function that returns the popup HTML for each point
    callback = """
    function (row) {
        var marker = L.marker(new L.LatLng(row[0], row[1]));
        marker.bindPopup('Endereço: ' + row[2] + '<br>Inscrição: ' + row[3]);
        return marker;
    };
    """

    # Prepare data for FastMarkerCluster
    data = [[row['latitude'], row['longitude'], row['endereco'], row['inscricao']] 
            for idx, row in valid_df.iterrows()]

    # Add FastMarkerCluster to the map
    FastMarkerCluster(data, callback=callback).add_to(m)
else:
    # Use regular MarkerCluster
    marker_cluster = MarkerCluster().add_to(m)

    # Add markers to the cluster
    for idx, row in valid_df.iterrows():
        folium.Marker(
            [row['latitude'], row['longitude']],
            popup=f"Endereço: {row['endereco']}<br>Inscrição: {row['inscricao']}"
        ).add_to(marker_cluster)

# Save the map
m.save(f'{input_filename}.html')
print(f"Map saved as {input_filename}.html")
