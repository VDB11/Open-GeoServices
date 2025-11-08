import os

# Directories
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
LOG_FOLDER = 'geo_logs'
TEMPLATE_FOLDER = 'templates'
DATA_FILE_PATH = "ETOPO_2022_v1_30s_N90W180_surface.nc"

# Create directories if they don't exist
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, LOG_FOLDER, TEMPLATE_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# API Settings
GEOCODING_API_URL = "https://geocoding.geo.census.gov/geocoder/locations/address"
GEOCODING_BENCHMARK = 'Public_AR_Current'
GEOCODING_FORMAT = 'json'

# File Settings
ZIPCODE_LOOKUP_FILE = 'usa_postcode_lookup.csv'
BATCH_SIZE = 10
MAX_WORKERS = 5
REQUEST_TIMEOUT = 5

# Reverse Geocoding Settings
REVERSE_GEOCODING_TIMEOUT = 10
REVERSE_GEOCODING_DELAY = 1

# Geocoding settings for global version
MAX_RETRIES = 1
NOMINATIM_DELAY = 5.0
PHOTON_DELAY = 2.0