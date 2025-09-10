from flask import Flask, request, jsonify, send_file, render_template
import os
import uuid
import threading
import time
import pandas as pd
from config import UPLOAD_FOLDER, OUTPUT_FOLDER
from utils import setup_logging, load_zipcode_lookup, parse_complete_address
from geocoder import process_address_file, geocode_single_address

app = Flask(__name__)
PROCESSING_STATUS = {}  # Track processing status

# Global variables
zip_dict = None
logger = None

def init_app():
    global zip_dict, logger
    logger = setup_logging()
    zip_dict = load_zipcode_lookup()
    logger.info(f"Loaded {len(zip_dict)} zipcode records")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/geocode/single', methods=['POST'])
def geocode_single():
    try:
        data = request.json
        address = data.get('address', '')
        
        if not address:
            return jsonify({'error': 'Address is required'}), 400
        
        address_dict = parse_complete_address(address)
        result = geocode_single_address(address_dict, zip_dict, logger)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in single geocoding: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/geocode/bulk', methods=['POST'])
def geocode_bulk():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        input_filename = os.path.join(UPLOAD_FOLDER, f"{file_id}_{file.filename}")
        output_filename = os.path.join(OUTPUT_FOLDER, f"result_{file_id}.csv")
        
        # Save uploaded file
        file.save(input_filename)
        
        # Initialize processing status
        PROCESSING_STATUS[file_id] = {
            'status': 'processing',
            'start_time': time.time(),
            'processed': 0,
            'total': 0
        }
        
        # Count rows in input file to set total
        if input_filename.endswith('.csv'):
            df = pd.read_csv(input_filename, header=None)
        elif input_filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(input_filename, header=None)
        
        PROCESSING_STATUS[file_id]['total'] = len(df)
        
        # Process file in background
        thread = threading.Thread(
            target=process_file_background,
            args=(input_filename, output_filename, file_id)
        )
        thread.start()
        
        return jsonify({
            'message': 'File uploaded successfully. Processing started.',
            'file_id': file_id
        })
    
    except Exception as e:
        logger.error(f"Error in bulk geocoding: {e}")
        return jsonify({'error': str(e)}), 500

def process_file_background(input_file, output_file, file_id):
    try:
        # Process file
        process_address_file(input_file, output_file, zip_dict, logger, file_id)
        
        # Update status to completed
        PROCESSING_STATUS[file_id]['status'] = 'completed'
        PROCESSING_STATUS[file_id]['end_time'] = time.time()
        
        # Clean up input file
        os.remove(input_file)
        
        logger.info(f"Processing completed for file ID: {file_id}")
    
    except Exception as e:
        PROCESSING_STATUS[file_id]['status'] = 'error'
        PROCESSING_STATUS[file_id]['error'] = str(e)
        logger.error(f"Error processing file {file_id}: {e}")

@app.route('/download/<file_id>')
def download_file(file_id):
    try:
        output_file = os.path.join(OUTPUT_FOLDER, f"result_{file_id}.csv")
        
        if not os.path.exists(output_file):
            return jsonify({'error': 'File not found'}), 404
        
        # Check if file is empty
        file_size = os.path.getsize(output_file)
        if file_size < 100:  # Approximate size of headers only
            return jsonify({'error': 'File is still being processed'}), 425 # TOO EARLY
        
        return send_file(
            output_file,
            as_attachment=True,
            download_name=f"geocoded_results_{file_id}.csv",
            mimetype='text/csv'
        )
    
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status/<file_id>')
def check_status(file_id):
    if file_id not in PROCESSING_STATUS:
        return jsonify({'error': 'Invalid file ID'}), 404
    
    status_info = PROCESSING_STATUS[file_id].copy()
    
    # Add file info if processing is complete
    if status_info['status'] == 'completed':
        output_file = os.path.join(OUTPUT_FOLDER, f"result_{file_id}.csv")
        if os.path.exists(output_file):
            status_info['file_size'] = os.path.getsize(output_file)
    
    return jsonify(status_info)

if __name__ == '__main__':
    init_app()
    app.run(debug=True, host='0.0.0.0', port=5000)