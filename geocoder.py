import pandas as pd
from geopy.geocoders import Nominatim, Photon
import time
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import requests
import logging
import sys
import os
from config import *

def setup_logging():
    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_FOLDER, f"geocoding_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

class CombinedGeocoder:
    def __init__(self):
        self.nominatim = Nominatim(user_agent="research_app", timeout=20)
        self.photon = Photon(user_agent="research_app", timeout=20)
        
    def geocode_with_nominatim(self, address, max_retries=MAX_RETRIES):
        for attempt in range(max_retries):
            try:
                location = self.nominatim.geocode(address)
                if location:
                    return location.latitude, location.longitude, location.address, "nominatim"
                else:
                    return None, None, "Not found", "nominatim"
                    
            except (GeocoderTimedOut, GeocoderServiceError, requests.exceptions.ReadTimeout) as e:
                if "403" in str(e) or "block" in str(e).lower():
                    return None, None, "Blocked by service", "nominatim_blocked"
                    
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    time.sleep(wait_time)
                else:
                    return None, None, f"Error: {str(e)}", "nominatim"
                    
        return None, None, "Max retries exceeded", "nominatim"
    
    def geocode_with_photon(self, address, max_retries=MAX_RETRIES):
        for attempt in range(max_retries):
            try:
                location = self.photon.geocode(address)
                if location:
                    return location.latitude, location.longitude, location.address, "photon"
                else:
                    return None, None, "Not found", "photon"
                    
            except (GeocoderTimedOut, GeocoderServiceError, requests.exceptions.ReadTimeout) as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    time.sleep(wait_time)
                else:
                    return None, None, f"Error: {str(e)}", "photon"
                    
        return None, None, "Max retries exceeded", "photon"
    
    def geocode_address(self, address, nominatim_blocked=False):
        # Try Nominatim first
        if not nominatim_blocked:
            lat1, lon1, full_addr1, service1 = self.geocode_with_nominatim(address)
            time.sleep(NOMINATIM_DELAY)
            
            if lat1 is not None:
                return lat1, lon1, full_addr1, service1
            
            if full_addr1 == "Blocked by service":
                return None, None, "Blocked by service", "nominatim_blocked"
        
        # Try Photon
        lat2, lon2, full_addr2, service2 = self.geocode_with_photon(address)
        time.sleep(PHOTON_DELAY)
        
        if lat2 is not None:
            return lat2, lon2, full_addr2, service2
        
        return None, None, "Not found in both services", "none"

def geocode_single_address_api(address_text, zip_dict, logger):
    geocoder = CombinedGeocoder()
    lat, lon, full_addr, service = geocoder.geocode_address(address_text)
    
    return {
        'input_address': address_text,
        'matched_address': full_addr,
        'lat': lat,
        'long': lon,
        'geo_service': service,
        'geocode_status': 'Success' if lat is not None else 'Failed'
    }

def process_address_file(input_file, output_file, zip_dict, logger):
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file, header=None)
    elif input_file.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(input_file, header=None)
    else:
        raise ValueError("Input file must be CSV or Excel format")
    
    output_columns = ['input_address', 'matched_address', 'lat', 'long', 'geo_service', 'geocode_status']
    
    output_df = pd.DataFrame(columns=output_columns)
    output_df.to_csv(output_file, index=False)
    
    geocoder = CombinedGeocoder()
    nominatim_blocked = False
    
    for index, row in df.iterrows():
        address = str(row[0])
        logger.info(f"Processing ({index+1}/{len(df)}): {address}")
        
        lat, lon, full_addr, service = geocoder.geocode_address(address, nominatim_blocked)
        
        if service == "nominatim_blocked":
            nominatim_blocked = True
            lat, lon, full_addr, service = geocoder.geocode_address(address, nominatim_blocked=True)
        
        result = {
            'input_address': address,
            'matched_address': full_addr,
            'lat': lat,
            'long': lon,
            'geo_service': service,
            'geocode_status': 'Success' if lat is not None else 'Failed'
        }
        
        result_df = pd.DataFrame([result])
        result_df = result_df[output_columns]
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            result_df.to_csv(output_file, mode='a', header=False, index=False)
        else:
            result_df.to_csv(output_file, index=False)
        
        if (index + 1) % 10 == 0:
            logger.info(f"Saved progress: {index + 1}/{len(df)}")
    
    logger.info(f"Processed {len(df)} addresses")
    return output_file

def load_zipcode_lookup(zipcode_file):
    return {}