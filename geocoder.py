import pandas as pd
import requests
import json
import time
import re
import sys
import os
import logging
from datetime import datetime
import concurrent.futures
import us  # For state code conversion
from config import *

def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_FOLDER, f"geocoding_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger()

def convert_state_code(state_code):
    """Convert state code to full state name using us library"""
    try:
        state = us.states.lookup(state_code)
        if state:
            return state.name
        return state_code  # Return original if not found
    except:
        return state_code

def load_zipcode_lookup(zipcode_file):
    if not os.path.exists(zipcode_file):
        raise FileNotFoundError(f"Zipcode lookup file {zipcode_file} not found")
    
    zip_df = pd.read_csv(zipcode_file)
    zip_dict = {}
    for _, row in zip_df.iterrows():
        zip_dict[str(row['postcode'])] = {
            'lat': row['lat'],
            'long': row['long'],
            'place': row['place']
        }
    return zip_dict

def parse_complete_address(address_line):
    address = address_line.split(', United States')[0].split(', USA')[0].strip()
    
    pattern = r'^(.*?),\s*([^,]+?),\s*([A-Za-z]{2})\s*(\d{5}(?:-\d{4})?)?$'
    match = re.match(pattern, address)
    
    if match:
        street, city, state, zip_code = match.groups()
        return {
            'street': street.strip(),
            'city': city.strip(),
            'state': state.strip().upper(),
            'zip': zip_code.strip() if zip_code else ''
        }
    
    parts = [part.strip() for part in address.split(',')]
    if len(parts) >= 3:
        street = parts[0]
        city = parts[1]
        last_part = parts[-1]
        state_zip_match = re.match(r'([A-Za-z]{2})\s*(\d{5}(?:-\d{4})?)?', last_part)
        
        if state_zip_match:
            state, zip_code = state_zip_match.groups()
            return {
                'street': street,
                'city': city,
                'state': state.upper(),
                'zip': zip_code if zip_code else ''
            }
    
    return {
        'street': address,
        'city': '',
        'state': '',
        'zip': ''
    }

def geocode_single_address(address_dict, zip_dict, logger):
    params = {
        'street': address_dict.get('street', '').replace(' ', '+'),
        'city': address_dict.get('city', '').replace(' ', '+'),
        'state': address_dict.get('state', ''),
        'zip': address_dict.get('zip', ''),
        'benchmark': GEOCODING_BENCHMARK,
        'format': GEOCODING_FORMAT
    }
    
    try:
        response = requests.get(GEOCODING_API_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('result', {}).get('addressMatches'):
            match = data['result']['addressMatches'][0]
            coords = match['coordinates']
            components = match['addressComponents']
            
            from_addr = components.get('fromAddress', '')
            to_addr = components.get('toAddress', '')
            building_range = f"{from_addr}-{to_addr}" if from_addr and to_addr else ""
            
            # Convert state code to full name
            state_name = convert_state_code(components.get('state', ''))
            
            return {
                'input_address': f"{address_dict.get('street', '')}, {address_dict.get('city', '')}, {address_dict.get('state', '')} {address_dict.get('zip', '')}",
                'matched_address': match.get('matchedAddress', ''),
                'lat': coords.get('y'),
                'long': coords.get('x'),
                'building_range': building_range,
                'street_name': components.get('streetName', ''),
                'suffix_type': components.get('suffixType', ''),
                'city_name': components.get('city', ''),
                'state_name': state_name,
                'postal_code': components.get('zip', ''),
                'postcode_lat': None,
                'postcode_long': None,
                'place': None
            }
        else:
            zip_code = address_dict.get('zip', '')
            zip_data = zip_dict.get(zip_code)
            
            # Convert state code to full name
            state_name = convert_state_code(address_dict.get('state', ''))
            
            result = {
                'input_address': f"{address_dict.get('street', '')}, {address_dict.get('city', '')}, {address_dict.get('state', '')} {address_dict.get('zip', '')}",
                'matched_address': 'Not Found',
                'lat': None,
                'long': None,
                'building_range': None,
                'street_name': None,
                'suffix_type': None,
                'city_name': None,
                'state_name': state_name,
                'postal_code': None,
                'postcode_lat': zip_data['lat'] if zip_data else None,
                'postcode_long': zip_data['long'] if zip_data else None,
                'place': zip_data['place'] if zip_data else None
            }
            
            if zip_data:
                logger.warning(f"No matches found for address, using zipcode centroid: {address_dict}")
            else:
                logger.warning(f"No matches found for address and no zipcode data: {address_dict}")
            
            return result
            
    except requests.exceptions.RequestException:
        zip_code = address_dict.get('zip', '')
        zip_data = zip_dict.get(zip_code)
        
        # Convert state code to full name
        state_name = convert_state_code(address_dict.get('state', ''))
        
        result = {
            'input_address': f"{address_dict.get('street', '')}, {address_dict.get('city', '')}, {address_dict.get('state', '')} {address_dict.get('zip', '')}",
            'matched_address': 'Not Found',
            'lat': None,
            'long': None,
            'building_range': None,
            'street_name': None,
            'suffix_type': None,
            'city_name': None,
            'state_name': state_name,
            'postal_code': None,
            'postcode_lat': zip_data['lat'] if zip_data else None,
            'postcode_long': zip_data['long'] if zip_data else None,
            'place': zip_data['place'] if zip_data else None
        }
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error for address {address_dict}: {e}")
        zip_code = address_dict.get('zip', '')
        zip_data = zip_dict.get(zip_code)
        
        # Convert state code to full name
        state_name = convert_state_code(address_dict.get('state', ''))
        
        return {
            'input_address': f"{address_dict.get('street', '')}, {address_dict.get('city', '')}, {address_dict.get('state', '')} {address_dict.get('zip', '')}",
            'matched_address': 'Not Found',
            'lat': None,
            'long': None,
            'building_range': None,
            'street_name': None,
            'suffix_type': None,
            'city_name': None,
            'state_name': state_name,
            'postal_code': None,
            'postcode_lat': zip_data['lat'] if zip_data else None,
            'postcode_long': zip_data['long'] if zip_data else None,
            'place': zip_data['place'] if zip_data else None
        }

def process_addresses_parallel(address_list, zip_dict, logger, max_workers=MAX_WORKERS):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_address = {
            executor.submit(geocode_single_address, addr, zip_dict, logger): addr 
            for addr in address_list
        }
        
        for future in concurrent.futures.as_completed(future_to_address):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Error in parallel processing: {e}")
    
    return results

def process_address_file(input_file, output_file, zip_dict, logger):
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file, header=None)
    elif input_file.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(input_file, header=None)
    else:
        raise ValueError("Input file must be CSV or Excel format")
    
    output_columns = [
        'input_address', 'matched_address', 'lat', 'long', 
        'building_range', 'street_name', 'suffix_type', 
        'city_name', 'state_name', 'postal_code',
        'postcode_lat', 'postcode_long', 'place'
    ]
    
    output_df = pd.DataFrame(columns=output_columns)
    output_df.to_csv(output_file, index=False)
    
    address_list = []
    for index, row in df.iterrows():
        complete_address = str(row[0])
        address_dict = parse_complete_address(complete_address)
        address_list.append(address_dict)
    
    for i in range(0, len(address_list), BATCH_SIZE):
        batch = address_list[i:i + BATCH_SIZE]
        logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(address_list)-1)//BATCH_SIZE + 1}")
        
        batch_results = process_addresses_parallel(batch, zip_dict, logger)
        
        batch_df = pd.DataFrame(batch_results)
        batch_df = batch_df[output_columns]
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            batch_df.to_csv(output_file, mode='a', header=False, index=False)
        else:
            batch_df.to_csv(output_file, index=False)
        
        logger.info(f"Saved batch {i//BATCH_SIZE + 1} to {output_file}")
    
    logger.info(f"Processed {len(address_list)} addresses")
    return output_file

def geocode_single_address_api(address_text, zip_dict, logger):
    """API-friendly single address geocoding"""
    address_dict = parse_complete_address(address_text)
    result = geocode_single_address(address_dict, zip_dict, logger)
    return result

def main():
    logger = setup_logging()
    
    if len(sys.argv) < 2:
        logger.error("Usage: python geocoder.py <input_file> [output_file]")
        logger.error("Example: python geocoder.py addresses.csv results.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'geocoded_results.csv'
    
    if not os.path.exists(input_file):
        logger.error(f"Input file '{input_file}' not found!")
        sys.exit(1)
    
    try:
        logger.info("Loading zipcode lookup data...")
        zip_dict = load_zipcode_lookup(ZIPCODE_LOOKUP_FILE)
        logger.info(f"Loaded {len(zip_dict)} zipcode records")
        
        logger.info(f"Starting geocoding process for {input_file}")
        process_address_file(input_file, output_file, zip_dict, logger)
        logger.info("Geocoding process completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()