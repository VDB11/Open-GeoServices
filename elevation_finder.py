import xarray as xr
import pandas as pd
import logging
import os
from config import DATA_FILE_PATH

# Load the elevation data
try:
    ds = xr.open_dataset(DATA_FILE_PATH)
    elevation_data = ds['z']
except Exception as e:
    print(f"Warning: Could not load elevation data: {e}")
    elevation_data = None

def get_elevation_for_coords(latitude, longitude, logger):
    """Get elevation for a single coordinate pair"""
    if elevation_data is None:
        logger.error("Elevation data not available")
        return None
    
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            logger.warning(f"Invalid coordinates: {latitude}, {longitude}")
            return None
        
        result = elevation_data.sel(
            lat=xr.DataArray([latitude], dims="points"),
            lon=xr.DataArray([longitude], dims="points"),
            method="nearest"
        )
        
        return float(result.values[0])
        
    except Exception as e:
        logger.error(f"Error getting elevation for {latitude},{longitude}: {str(e)}")
        return None

def process_elevation_file(input_file, output_file, logger):
    """Process a file with coordinates to get elevations"""
    if elevation_data is None:
        logger.error("Elevation data not available for processing")
        return None
    
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file, header=None)
    elif input_file.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(input_file, header=None)
    else:
        raise ValueError("Input file must be CSV or Excel format")
    
    output_columns = ['input_coordinates', 'latitude', 'longitude', 'elevation', 'error']
    
    output_df = pd.DataFrame(columns=output_columns)
    output_df.to_csv(output_file, index=False)
    
    results = []
    for index, row in df.iterrows():
        coord_str = str(row[0]).strip()
        try:
            lat_str, lon_str = coord_str.split(',')
            latitude = float(lat_str.strip())
            longitude = float(lon_str.strip())
            
            elevation = get_elevation_for_coords(latitude, longitude, logger)
            
            results.append({
                'input_coordinates': coord_str,
                'latitude': latitude,
                'longitude': longitude,
                'elevation': elevation,
                'error': None if elevation is not None else 'Error getting elevation'
            })
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Invalid coordinate format: {coord_str}")
            results.append({
                'input_coordinates': coord_str,
                'latitude': None,
                'longitude': None,
                'elevation': None,
                'error': f'Invalid format: {str(e)}'
            })
    
    # Save all results at once
    results_df = pd.DataFrame(results)
    results_df = results_df[output_columns]
    results_df.to_csv(output_file, index=False)
    
    logger.info(f"Processed {len(results)} coordinate pairs for elevation")
    return output_file