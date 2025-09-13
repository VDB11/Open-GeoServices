from flask import Flask, render_template, request, send_file, jsonify, flash, redirect, url_for
import os
import uuid
from datetime import datetime
from geocoder import load_zipcode_lookup, geocode_single_address_api, process_address_file, setup_logging
from reverse_geocoding import setup_reverse_geocoding, reverse_geocode_single, process_reverse_geocoding_file
from elevation_finder import get_elevation_for_coords, process_elevation_file
from config import *

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your-secret-key-here'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Initialize components
    logger = setup_logging()
    try:
        zip_dict = load_zipcode_lookup(ZIPCODE_LOOKUP_FILE)
        logger.info(f"Loaded {len(zip_dict)} zipcode records")
    except Exception as e:
        logger.error(f"Failed to load zipcode data: {e}")
        zip_dict = {}

    # Initialize reverse geocoder
    try:
        reverse_geocoder = setup_reverse_geocoding()
        logger.info("Reverse geocoder initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize reverse geocoder: {e}")
        reverse_geocoder = None

    # Store in app context
    app.logger_instance = logger
    app.zip_dict = zip_dict
    app.reverse_geocoder = reverse_geocoder

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/geocode/single', methods=['POST'])
    def geocode_single():
        try:
            address = request.form.get('address', '').strip()
            if not address:
                return jsonify({'error': 'Address is required'}), 400
            
            result = geocode_single_address_api(address, app.zip_dict, app.logger_instance)
            return jsonify(result)
        
        except Exception as e:
            app.logger_instance.error(f"Error in single address geocoding: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/geocode/bulk', methods=['POST'])
    def geocode_bulk():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if file and (file.filename.endswith('.csv') or file.filename.endswith(('.xlsx', '.xls'))):
                # Generate unique filename
                file_id = str(uuid.uuid4())
                original_filename = file.filename
                file_extension = os.path.splitext(original_filename)[1]
                input_filename = f"{file_id}{file_extension}"
                output_filename = f"{file_id}_geocoded.csv"
                
                input_path = os.path.join(UPLOAD_FOLDER, input_filename)
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)
                
                # Save uploaded file
                file.save(input_path)
                app.logger_instance.info(f"Saved uploaded file: {input_path}")
                
                # Process the file
                process_address_file(input_path, output_path, app.zip_dict, app.logger_instance)
                
                return jsonify({
                    'success': True,
                    'file_id': file_id,
                    'output_filename': output_filename,
                    'original_filename': original_filename
                })
            else:
                return jsonify({'error': 'Invalid file format. Please upload CSV or Excel file.'}), 400
        
        except Exception as e:
            app.logger_instance.error(f"Error in bulk geocoding: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/reverse-geocode/single', methods=['POST'])
    def reverse_geocode_single_route():
        try:
            coords = request.form.get('coordinates', '').strip()
            if not coords:
                return jsonify({'error': 'Coordinates are required'}), 400
            
            try:
                lat_str, lon_str = coords.split(',')
                coords_dict = {
                    'lat': float(lat_str.strip()),
                    'lon': float(lon_str.strip())
                }
            except (ValueError, IndexError):
                return jsonify({'error': 'Invalid coordinate format. Use: latitude,longitude'}), 400
            
            if app.reverse_geocoder is None:
                return jsonify({'error': 'Reverse geocoding service not available'}), 500
            
            result = reverse_geocode_single(coords_dict, app.reverse_geocoder, app.logger_instance)
            return jsonify(result)
        
        except Exception as e:
            app.logger_instance.error(f"Error in single reverse geocoding: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/reverse-geocode/bulk', methods=['POST'])
    def reverse_geocode_bulk():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if file and (file.filename.endswith('.csv') or file.filename.endswith(('.xlsx', '.xls'))):
                # Generate unique filename
                file_id = str(uuid.uuid4())
                original_filename = file.filename
                file_extension = os.path.splitext(original_filename)[1]
                input_filename = f"{file_id}{file_extension}"
                output_filename = f"{file_id}_reverse_geocoded.csv"
                
                input_path = os.path.join(UPLOAD_FOLDER, input_filename)
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)
                
                # Save uploaded file
                file.save(input_path)
                app.logger_instance.info(f"Saved uploaded file for reverse geocoding: {input_path}")
                
                if app.reverse_geocoder is None:
                    return jsonify({'error': 'Reverse geocoding service not available'}), 500
                
                # Process the file
                process_reverse_geocoding_file(input_path, output_path, app.reverse_geocoder, app.logger_instance)
                
                return jsonify({
                    'success': True,
                    'file_id': file_id,
                    'output_filename': output_filename,
                    'original_filename': original_filename
                })
            else:
                return jsonify({'error': 'Invalid file format. Please upload CSV or Excel file.'}), 400
        
        except Exception as e:
            app.logger_instance.error(f"Error in bulk reverse geocoding: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/elevation/single', methods=['POST'])
    def elevation_single():
        try:
            coords = request.form.get('coordinates', '').strip()
            if not coords:
                return jsonify({'error': 'Coordinates are required'}), 400
            
            try:
                lat_str, lon_str = coords.split(',')
                latitude = float(lat_str.strip())
                longitude = float(lon_str.strip())
            except (ValueError, IndexError):
                return jsonify({'error': 'Invalid coordinate format. Use: latitude,longitude'}), 400
            
            elevation = get_elevation_for_coords(latitude, longitude, app.logger_instance)
            
            if elevation is None:
                return jsonify({'error': 'Could not retrieve elevation data'}), 500
            
            return jsonify({
                'input_coordinates': coords,
                'latitude': latitude,
                'longitude': longitude,
                'elevation': elevation
            })
        
        except Exception as e:
            app.logger_instance.error(f"Error in single elevation lookup: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/elevation/bulk', methods=['POST'])
    def elevation_bulk():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if file and (file.filename.endswith('.csv') or file.filename.endswith(('.xlsx', '.xls'))):
                # Generate unique filename
                file_id = str(uuid.uuid4())
                original_filename = file.filename
                file_extension = os.path.splitext(original_filename)[1]
                input_filename = f"{file_id}{file_extension}"
                output_filename = f"{file_id}_elevation.csv"
                
                input_path = os.path.join(UPLOAD_FOLDER, input_filename)
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)
                
                # Save uploaded file
                file.save(input_path)
                app.logger_instance.info(f"Saved uploaded file for elevation: {input_path}")
                
                # Process the file
                process_elevation_file(input_path, output_path, app.logger_instance)
                
                return jsonify({
                    'success': True,
                    'file_id': file_id,
                    'output_filename': output_filename,
                    'original_filename': original_filename
                })
            else:
                return jsonify({'error': 'Invalid file format. Please upload CSV or Excel file.'}), 400
        
        except Exception as e:
            app.logger_instance.error(f"Error in bulk elevation lookup: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/download/<filename>')
    def download_file(filename):
        try:
            file_path = os.path.join(OUTPUT_FOLDER, filename)
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
            else:
                return jsonify({'error': 'File not found'}), 404
        except Exception as e:
            app.logger_instance.error(f"Error downloading file: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/list-files')
    def list_files():
        try:
            files = []
            for filename in os.listdir(OUTPUT_FOLDER):
                if filename.endswith('.csv'):
                    file_path = os.path.join(OUTPUT_FOLDER, filename)
                    files.append({
                        'filename': filename,
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                    })
            return jsonify({'files': files})
        except Exception as e:
            app.logger_instance.error(f"Error listing files: {e}")
            return jsonify({'error': str(e)}), 500

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)