import pandas as pd
import logging
import sys
import os
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import *

def setup_reverse_geocoding():
    """Set up reverse geocoding with rate limiting and retry logic"""
    # Create a session with retry logic
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Initialize geolocator with rate limiting
    geolocator = Nominatim(
        user_agent="reverse_geocoding_app",
        timeout=REVERSE_GEOCODING_TIMEOUT,
        scheme='http'
    )
    reverse = RateLimiter(geolocator.reverse, min_delay_seconds=REVERSE_GEOCODING_DELAY)
    
    return reverse

def is_valid_coordinate(lat, lon):
    """Check if coordinates are valid"""
    try:
        lat = float(lat)
        lon = float(lon)
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (ValueError, TypeError):
        return False

def reverse_geocode_single(coords_dict, reverse_geocoder, logger):
    """Reverse geocode a single coordinate pair"""
    latitude = coords_dict.get('lat')
    longitude = coords_dict.get('lon')
    
    if not is_valid_coordinate(latitude, longitude):
        logger.warning(f"Invalid coordinates: {latitude}, {longitude}")
        return {
            'input_coordinates': f"{latitude},{longitude}",
            'full_address': 'Invalid coordinates',
            'street': 'Invalid',
            'locality': 'Invalid',
            'district': 'Invalid',
            'city': 'Invalid',
            'town': 'Invalid',
            'state': 'Invalid',
            'country': 'Invalid',
            'postcode': 'Invalid',
            'province': 'Invalid',
            'error': 'Invalid coordinates provided'
        }
    
    try:
        location = reverse_geocoder((latitude, longitude), language='en', exactly_one=True)
        
        if not location:
            logger.warning(f"No location found for coordinates: {latitude},{longitude}")
            return {
                'input_coordinates': f"{latitude},{longitude}",
                'full_address': 'Not found',
                'street': 'Not found',
                'locality': 'Not found',
                'district': 'Not found',
                'city': 'Not found',
                'town': 'Not found',
                'state': 'Not found',
                'country': 'Not found',
                'postcode': 'Not found',
                'province': 'Not found',
                'error': 'No location found'
            }
        
        address_details = location.raw.get('address', {})
        
        return {
            'input_coordinates': f"{latitude},{longitude}",
            'full_address': location.address,
            'street': address_details.get('road', 'Not available'),
            'locality': address_details.get('suburb', address_details.get('locality', 'Not available')),
            'district': address_details.get('district', 'Not available'),
            'city': address_details.get('city', 'Not available'),
            'town': address_details.get('town', address_details.get('suburb', 'Not available')),
            'state': address_details.get('state', 'Not available'),
            'country': address_details.get('country', 'Not available'),
            'postcode': address_details.get('postcode', 'Not available'),
            'province': address_details.get('province', 'Not available'),
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error reverse geocoding {latitude},{longitude}: {str(e)}")
        return {
            'input_coordinates': f"{latitude},{longitude}",
            'full_address': 'Error',
            'street': 'Error',
            'locality': 'Error',
            'district': 'Error',
            'city': 'Error',
            'town': 'Error',
            'state': 'Error',
            'country': 'Error',
            'postcode': 'Error',
            'province': 'Error',
            'error': str(e)
        }

def process_reverse_geocoding_file(input_file, output_file, reverse_geocoder, logger):
    """Process a file with coordinates for reverse geocoding"""
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file, header=None)
    elif input_file.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(input_file, header=None)
    else:
        raise ValueError("Input file must be CSV or Excel format")
    
    output_columns = [
        'input_coordinates', 'full_address', 'street', 'locality', 
        'district', 'city', 'town', 'state', 'country', 'postcode', 
        'province', 'error'
    ]
    
    output_df = pd.DataFrame(columns=output_columns)
    output_df.to_csv(output_file, index=False)
    
    coords_list = []
    for index, row in df.iterrows():
        coord_str = str(row[0]).strip()
        try:
            lat_str, lon_str = coord_str.split(',')
            coords_list.append({
                'lat': float(lat_str.strip()),
                'lon': float(lon_str.strip())
            })
        except (ValueError, IndexError):
            logger.warning(f"Invalid coordinate format: {coord_str}")
            coords_list.append({
                'lat': None,
                'lon': None
            })
    
    for i in range(0, len(coords_list), BATCH_SIZE):
        batch = coords_list[i:i + BATCH_SIZE]
        logger.info(f"Processing reverse geocoding batch {i//BATCH_SIZE + 1}/{(len(coords_list)-1)//BATCH_SIZE + 1}")
        
        batch_results = []
        for coords in batch:
            result = reverse_geocode_single(coords, reverse_geocoder, logger)
            batch_results.append(result)
        
        batch_df = pd.DataFrame(batch_results)
        batch_df = batch_df[output_columns]
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            batch_df.to_csv(output_file, mode='a', header=False, index=False)
        else:
            batch_df.to_csv(output_file, index=False)
        
        logger.info(f"Saved reverse geocoding batch {i//BATCH_SIZE + 1} to {output_file}")
    
    logger.info(f"Processed {len(coords_list)} coordinate pairs")
    return output_file