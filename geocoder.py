import os
import requests
import concurrent.futures
import pandas as pd
from config import GEOCODING_API_URL, GEOCODING_BENCHMARK, GEOCODING_FORMAT, REQUEST_TIMEOUT, BATCH_SIZE, MAX_WORKERS
from utils import convert_state_code, convert_state_to_code

# Geocode a single address
def geocode_single_address(address_dict, zip_dict, logger):
    state_for_api = address_dict.get('state', '')
    if len(state_for_api) > 2:
        state_for_api = convert_state_to_code(state_for_api)
    
    params = {
        'street': address_dict.get('street', '').replace(' ', '+'),
        'city': address_dict.get('city', '').replace(' ', '+'),
        'state': state_for_api,
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
            
            result = {
                'input_address': f"{address_dict.get('street', '')}, {address_dict.get('city', '')}, {address_dict.get('state', '')} {address_dict.get('zip', '')}",
                'matched_address': 'Not Found',
                'lat': None,
                'long': None,
                'building_range': None,
                'street_name': None,
                'suffix_type': None,
                'city_name': None,
                'state_name': address_dict.get('state', ''),
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
        
        result = {
            'input_address': f"{address_dict.get('street', '')}, {address_dict.get('city', '')}, {address_dict.get('state', '')} {address_dict.get('zip', '')}",
            'matched_address': 'Not Found',
            'lat': None,
            'long': None,
            'building_range': None,
            'street_name': None,
            'suffix_type': None,
            'city_name': None,
            'state_name': address_dict.get('state', ''),
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
        
        return {
            'input_address': f"{address_dict.get('street', '')}, {address_dict.get('city', '')}, {address_dict.get('state', '')} {address_dict.get('zip', '')}",
            'matched_address': 'Not Found',
            'lat': None,
            'long': None,
            'building_range': None,
            'street_name': None,
            'suffix_type': None,
            'city_name': None,
            'state_name': address_dict.get('state', ''),
            'postal_code': None,
            'postcode_lat': zip_data['lat'] if zip_data else None,
            'postcode_long': zip_data['long'] if zip_data else None,
            'place': zip_data['place'] if zip_data else None
        }

# Process addresses in parallel using ThreadPoolExecutor
def process_addresses_parallel(address_list, zip_dict, logger):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
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

# Process a file of addresses in batches
def process_address_file(input_file, output_file, zip_dict, logger, file_id=None, status_callback=None):
    # Read input file
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
    
    # Create empty output file with headers
    output_df = pd.DataFrame(columns=output_columns)
    output_df.to_csv(output_file, index=False)
    
    # Parse addresses
    from utils import parse_complete_address
    address_list = []
    for index, row in df.iterrows():
        complete_address = str(row[0])
        address_dict = parse_complete_address(complete_address)
        address_list.append(address_dict)
    
    # Process in batches
    total_batches = (len(address_list) - 1) // BATCH_SIZE + 1
    
    for i in range(0, len(address_list), BATCH_SIZE):
        batch = address_list[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        logger.info(f"Processing batch {batch_num}/{total_batches}")

        if status_callback and file_id:
            status_callback(file_id, i + len(batch), len(address_list))
        
        batch_results = process_addresses_parallel(batch, zip_dict, logger)
        
        batch_df = pd.DataFrame(batch_results)
        batch_df = batch_df[output_columns]
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            batch_df.to_csv(output_file, mode='a', header=False, index=False)
        else:
            batch_df.to_csv(output_file, index=False)
        
        logger.info(f"Saved batch {batch_num} to {output_file}")
    
    logger.info(f"Processed {len(address_list)} addresses")
    return output_file