import requests
import argparse

def test_geoapify_api(endereco):
    """Test the Geoapify API with the given address"""
    url = f'http://localhost:8080/external/geocode-geoapify?address={endereco}'
    print(f"Testing Geoapify API with URL: {url}")

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("API Response:")
            print(data)

            # Check if features exist and have coordinates
            if 'features' in data and data['features']:
                for i, feature in enumerate(data['features']):
                    if 'geometry' in feature and 'coordinates' in feature['geometry']:
                        coords = feature['geometry']['coordinates']
                        print(f"Feature {i} coordinates: {coords}")
                    else:
                        print(f"Feature {i} has no coordinates")
            else:
                print("No features found in response")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Exception: {e}")

def test_google_api(endereco):
    """Test the Google API with the given address"""
    url = f'http://localhost:8080/external/geocode?address={endereco}'
    print(f"Testing Google API with URL: {url}")

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("API Response:")
            print(data)

            # Check if results exist and have location
            if 'results' in data and data['results']:
                for i, result in enumerate(data['results']):
                    if 'geometry' in result and 'location' in result['geometry']:
                        location = result['geometry']['location']
                        print(f"Result {i} location: lat={location['lat']}, lng={location['lng']}")
                    else:
                        print(f"Result {i} has no location")
            else:
                print("No results found in response")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Test geocoding APIs')
    parser.add_argument('--api', choices=['geoapify', 'google', 'both'], default='both',
                        help='API to test (default: both)')
    parser.add_argument('--address', default="AVENIDA JULIO SCHEIBE, 1065, HONÓRIO SERPA PARANA",
                        help='Address to geocode (default: AVENIDA JULIO SCHEIBE, 1065, HONÓRIO SERPA PARANA)')
    args = parser.parse_args()

    # Test the selected API(s)
    if args.api in ['geoapify', 'both']:
        print("\n=== Testing Geoapify API ===")
        test_geoapify_api(args.address)

    if args.api in ['google', 'both']:
        print("\n=== Testing Google API ===")
        test_google_api(args.address)
