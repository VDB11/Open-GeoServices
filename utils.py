import logging
import os
import pandas as pd
import re
import us
from datetime import datetime
from config import LOG_FOLDER, ZIPCODE_LOOKUP_FILE

def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_FOLDER, f"geocoding_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger()

# Convert state code to full state name
def convert_state_code(state_code):
    try:
        state = us.states.lookup(state_code)
        if state:
            return state.name
        return state_code
    except:
        return state_code

# Convert state name to state code
def convert_state_to_code(state_name):
    try:
        state = us.states.lookup(state_name)
        if state:
            return state.abbr
        return state_name
    except:
        return state_name

# Parse a complete address string into components
def parse_complete_address(address_line):
    address = address_line.split(', United States')[0].split(', USA')[0].strip()
    
    pattern = r'^(.*?),\s*([^,]+?),\s*([A-Za-z]{2})\s*(\d{5}(?:-\d{4})?)?$'
    match = re.match(pattern, address)
    
    if match:
        street, city, state, zip_code = match.groups()
        return {
            'street': street.strip(),
            'city': city.strip(),
            'state': convert_state_code(state.strip().upper()),
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
                'state': convert_state_code(state.upper()),
                'zip': zip_code if zip_code else ''
            }
    
    return {
        'street': address,
        'city': '',
        'state': '',
        'zip': ''
    }

# Load zipcode lookup data from CSV file
def load_zipcode_lookup():
    if not os.path.exists(ZIPCODE_LOOKUP_FILE):
        raise FileNotFoundError(f"Zipcode lookup file {ZIPCODE_LOOKUP_FILE} not found")
    
    zip_df = pd.read_csv(ZIPCODE_LOOKUP_FILE)
    zip_dict = {}
    for _, row in zip_df.iterrows():
        zip_dict[str(row['postcode'])] = {
            'lat': row['lat'],
            'long': row['long'],
            'place': row['place']
        }
    return zip_dict