# OPEN GEOSERVICES

A comprehensive open-source, Flask-based web application for geospatial data processing including geocoding, reverse geocoding, and elevation lookup services.

## 🌟 Features

### 1. Geocoding
- Convert addresses to geographic coordinates (Currently only works for US addresses)
- Automatic address parsing and validation
- Fallback to postalcode centroids when addresses aren't found
- Batch processing for multiple addresses with parallel execution
- State code to full state name conversion
- Support for various address formats

### 2. Reverse Geocoding  
- Convert coordinates to human-readable addresses
- Comprehensive address component extraction (street, city, state, country, etc.)
- Rate limiting and retry logic for reliable API calls
- Batch processing support for multiple coordinates
- Coordinate validation and error handling
- Worldwide coverage

### 3. Elevation Lookup
- Get elevation data (MSL) for any set of coordinates
- High-resolution (30 arc-second) elevation data
- Nearest-neighbor interpolation for accurate results
- Bulk processing capabilities for multiple coordinates
- Support for worldwide coordinates

### 4. Web Interface
- Real-time single query processing with instant results
- Bulk file upload and download functionality
- File management system with download history
- Progress indicators and error handling

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- 4GB+ RAM recommended for large files
- 2GB+ disk space for elevation data
- Internet connection for geocoding services

### Setup Steps

1. **Clone or download the project files:**
```bash
git clone https://github.com/VDB11/Open-GeoServices.git
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Download elevation data:**
   - Obtain the ETOPO 2022 dataset: `ETOPO_2022_v1_30s_N90W180_surface.nc` from 
   - Download from NOAA or other geographic data providers (Example: https://www.ncei.noaa.gov/products)
   - Place the file in the project root directory
   - Compatible with a higher resolution (15 arc-second) version. Download the data for higher accuracy.

4. **Directory structure (auto-created on first run):**
```
Open-GeoServices/
├── uploads/           # Temporary file storage (user uploads)
├── outputs/           # Processed results (downloadable files)
├── geo_logs/          # Application logs
├── templates/         # HTML templates
├── app.py             # Main Flask application
├── config.py          # Configuration settings
├── geocoder.py        # Forward geocoding functionality
├── reverse_geocoding.py # Reverse geocoding functionality
├── elevation_finder.py # Elevation lookup service
├── run.py             # Application runner
├── requirements.txt   # Python dependencies
└── ETOPO_2022_v1_30s_N90W180_surface.nc  # Raster dataset
```

## 📖 Usage

### Running the Application
```bash
python run.py
```

Access the application at: `http://localhost:5000`

### File Formats

**For Address Geocoding (CSV/Excel):**
```
1600 Pennsylvania Ave NW, Washington, DC 20500
123 Main Street, Anytown, CA 90210
```

**For Reverse Geocoding & Elevation (CSV/Excel):**
```
38.8977, -77.0365
34.0522, -118.2437
51.5074, -0.1278
```

### Single Query Processing
1. **Forward Geocoding Tab**: Enter a complete address
2. **Reverse Geocoding Tab**: Enter coordinates as `latitude,longitude`
3. **Elevation Tab**: Enter coordinates as `latitude,longitude`

### Bulk Processing
1. **Bulk Processing Tab**: Upload CSV/Excel files
2. **File Requirements**: Single column with addresses or coordinates
3. **Download**: Processed files available in download section

## 🔗 API Endpoints

- `POST /geocode/single` - Single address geocoding
- `POST /geocode/bulk` - Bulk address geocoding
- `POST /reverse-geocode/single` - Single coordinate reverse geocoding
- `POST /reverse-geocode/bulk` - Bulk coordinate reverse geocoding
- `POST /elevation/single` - Single coordinate elevation lookup
- `POST /elevation/bulk` - Bulk coordinate elevation lookup
- `GET /download/<filename>` - Download processed files
- `GET /list-files` - List available output files

## 🐛 Troubleshooting

### Common Issues
1. **Elevation data not found**: Ensure `ETOPO_2022_v1_30s_N90W180_surface.nc` is in project root
2. **Geocoding API errors**: Check internet connection and API status
3. **File upload issues**: Verify format. All input values should be in the one column (no headers needed).

### Logs
Check `geo_logs/` directory for detailed error logs and processing history

## 📝 License

This project uses only open source data. Please ensure compliance with:
- US Census Bureau API terms of service
- Nominatim usage policies
- ETOPO dataset licensing terms