from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session, jsonify, make_response
from flask_cors import CORS
import os
import sys
import logging
from datetime import datetime
import zipfile
import io
from werkzeug.utils import secure_filename
import secrets
from pathlib import Path
import shutil
from scripts.split_tmx import split_by_language, split_by_size
from scripts.convert_vatv import process_csv_file
from scripts.convert_termweb import process_excel_file
from scripts.batch_process import batch_process_1_5, batch_process_1_5_9
from scripts.merge_tmx import merge_tmx_files
from scripts.xliff_operations import leverage_tmx_into_xliff, check_empty_targets
from scripts.clean_tmx_for_mt import clean_tmx_for_mt
import json
from dependency_manager import DependencyManager, DependencyCategories


# Configure logging before anything else
logging.basicConfig(
    filename='tmx_tool.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Get the absolute path to PythonTmx
project_root = os.path.dirname(os.path.abspath(__file__))
tmx_path = os.path.join(project_root, 'tmx', 'Lib', 'site-packages')
pythontmx_path = os.path.join(tmx_path, 'PythonTmx')

# Add both paths to sys.path before any imports
if pythontmx_path not in sys.path:
    sys.path.insert(0, pythontmx_path)
if tmx_path not in sys.path:
    sys.path.insert(0, tmx_path)

# Import PythonTmx first before other imports
try:
    import PythonTmx
    logger.info("Successfully imported PythonTmx")
except ImportError as e:
    logger.critical(f"Failed to import PythonTmx: {e}")
    raise

# Import your existing functions from the scripts package
try:
    from scripts.remove_old import remove_old_tus
    from scripts import (empty_targets, find_true_duplicates, 
                        extract_non_true_duplicates, find_sentence_level_segments,
                        convert_vatv_to_tmx, convert_termweb_to_tmx, merge_tmx_files,
                        clean_tmx_for_mt)
    from scripts.batch_process import batch_process_1_5, batch_process_1_5_9
    from scripts.extract_translations import extract_translations
    from scripts.count_creation_dates import count_creation_dates
    from scripts.count_last_usage import count_last_usage_dates
    from scripts.find_date_duplicates import process_file as find_date_duplicates
except ImportError as e:
    logger.critical(f"Failed to import script modules: {e}")
    raise

# Update the Flask app initialization section
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    app = Flask(__name__, 
                template_folder=template_folder,
                static_folder=os.path.join(template_folder, 'static'))
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Application Configuration
app.config.update(
    UPLOAD_FOLDER=os.path.join(application_path, 'uploads'),
    MAX_CONTENT_LENGTH=1024 * 1024 * 1024,  # 1024MB max file size
    SECRET_KEY=secrets.token_hex(32),
    SESSION_COOKIE_SECURE=False,  # Allow HTTP in development
    SESSION_COOKIE_HTTPONLY=True,
    PERMANENT_SESSION_LIFETIME=7200,  # 2 hours session lifetime
    MAX_PROCESSING_TIME=14400  # 4 hours maximum processing time
)

# Ensure upload directory exists
upload_dir = Path(app.config['UPLOAD_FOLDER'])
upload_dir.mkdir(parents=True, exist_ok=True)

def cleanup_old_files():
    """Clean up files older than 4 hours"""
    try:
        current_time = datetime.now()
        for file_path in upload_dir.glob('*'):
            if file_path.is_file():
                file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age.total_seconds() > app.config['MAX_PROCESSING_TIME']:
                    os.remove(file_path)
    except Exception as e:
        logger.error(f"Error cleaning up old files: {e}")

def send_processed_files(files, base_filename, operation_name):
    """Helper function to zip and send multiple processed files"""
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in files if isinstance(files, list) else [files]:
                if os.path.exists(file_path):
                    zf.write(file_path, os.path.basename(file_path))
                    # Clean up the processed file after adding to zip
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Could not remove processed file {file_path}: {e}")
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{operation_name}_{base_filename}.zip'
        )
    except Exception as e:
        logger.error(f"Error creating zip file: {e}")
        raise

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'tmx', 'csv', 'xlsx', 'xls', 'zip'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def before_request():
    """Operations to perform before each request"""
    cleanup_old_files()
    if not session.get('csrf_token'):
        session['csrf_token'] = secrets.token_hex(32)

def handle_tmx_operation(func):
    """Decorator to handle TMX operations and their errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        #except PythonTmx.TmxError as e:
        #    logger.error(f"TMX processing error in {func.__name__}: {e}")
        #    raise ValueError(f"TMX processing error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise
    return wrapper

# Update OPERATIONS to use the decorator
OPERATIONS = {
    'convert_vatv': handle_tmx_operation(convert_vatv_to_tmx),
    'convert_termweb': handle_tmx_operation(convert_termweb_to_tmx),
    'remove_empty': handle_tmx_operation(empty_targets),
    'find_duplicates': handle_tmx_operation(find_true_duplicates),
    'non_true_duplicates': handle_tmx_operation(extract_non_true_duplicates),
    'clean_mt': handle_tmx_operation(clean_tmx_for_mt),
    'merge_tmx': handle_tmx_operation(merge_tmx_files),
    'split_language': handle_tmx_operation(split_by_language),
    'split_size': handle_tmx_operation(split_by_size),
    'batch_process_tms': handle_tmx_operation(batch_process_1_5),
    'batch_process_mt': handle_tmx_operation(batch_process_1_5_9)
}

@app.route('/api/check-feature', methods=['GET'])
def check_feature():
    feature = request.args.get('feature')
    if not feature:
        return jsonify({'error': 'Feature parameter required'}), 400
    
    dep_manager = DependencyManager(get_application_path())
    feature_deps = DependencyCategories.OPTIONAL_FEATURES.get(feature, [])
    
    available = all(dep_manager.is_package_installed(dep) for dep in feature_deps)
    return jsonify({'available': available})

@app.route('/api/install-feature', methods=['POST'])
def install_feature():
    data = request.get_json()
    feature = data.get('feature')
    
    if not feature:
        return jsonify({'error': 'Feature parameter required'}), 400
    
    dep_manager = DependencyManager(get_application_path())
    feature_deps = DependencyCategories.OPTIONAL_FEATURES.get(feature, [])
    
    if not feature_deps:
        return jsonify({'error': 'Unknown feature'}), 400
    
    success = True
    for dep in feature_deps:
        if not dep_manager.install_package(dep):
            success = False
            break
    
    return jsonify({'success': success})

@app.route('/queue/', methods=['GET', 'POST'])
def queue():
    if request.method == 'POST':
        try:
            data = request.form
            operations = json.loads(data.get('operations', '[]'))
            files = request.files.getlist('file')
            result = None
            garbage = []
            
            file_list = []
            for file in files:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_list.append(filepath)
                file.save(filepath)

            for operation in operations:
                result_list = None
                if result == None:
                    result_list = process_file(operation, file_list[0])
                else:
                    result_list = process_file(operation, result)
                if type(result_list) == tuple and len(result_list) > 1 :
                    result = result_list[0]
                    garbage.append(result_list[1])
                else:
                    result = result_list
                

            result_list2 = [result]
            result_list2.extend(garbage)

            result_list = tuple(result_list)
            memory_file = io.BytesIO()
            
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    if operation in ('convert_vatv','clean_mt','merge_tmx'):
                        if type(result_list) == str:
                            zf.write(result_list, os.path.basename(result_list))
                        else:
                            file_path = result_list[0]
                            zf.write(file_path, os.path.basename(file_path))
                    else:
                        for result in result_list:
                            if len(result) > 2:
                                if os.path.exists(result):
                                    zf.write(result, os.path.basename(result))
                            else:
                                for tm in result:
                                    if os.path.exists(tm):
                                        zf.write(tm, os.path.basename(tm))




            memory_file.seek(0)

            # Handle different result types
            if isinstance(memory_file, io.BytesIO):
                return send_file(
                    memory_file,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=f'{operation}_multiple.zip'
                )
            else:
                return send_file(
                    memory_file,
                    as_attachment=True,
                    download_name=f'{operation}_multiple'
                )



        except Exception as e:
            logger.error(f"Error processing queue: {e}")
            return jsonify({'error': str(e)}), 400






@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # Validate file
            if 'file' not in request.files:
                if is_api_request():
                    return jsonify({'error': 'No file uploaded'}), 400
                else:
                    flash('No file uploaded', 'error')
                    return redirect(url_for('index'))
            
            
            
            files = request.files.getlist('file')
            for file in files:
                if not files or not file.filename:
                    if is_api_request():
                        return jsonify({'error': 'No file selected'}), 400
                    else:
                        flash('No file selected', 'error')
                        return redirect(url_for('index'))

            for file in files:    
                if not allowed_file(file.filename):
                    if is_api_request():
                        return jsonify({'error': 'Invalid file type'}), 400
                    else:
                        flash('Invalid file type', 'error')
                        return redirect(url_for('index'))

            # Get operation
            operation = request.form.get('operation')
            if not operation:
                if is_api_request():
                    return jsonify({'error': 'No operation selected'}), 400
                else:
                    flash('No operation selected', 'error')
                    return redirect(url_for('index'))

            # Save and process file
            file_list = []
            for file in files:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_list.append(filepath)
                file.save(filepath)
            try:
                result_list = None
                if len(file_list) > 1:
                    if operation == 'merge_tmx':
                        result_list = process_file(operation, file_list)
                    elif operation == 'split_size':
                        result_list = split_by_size(file_list, request.form.get('size'))
                    else:
                        result_list = []
                        for file in file_list:
                            result = process_file(operation, file)
                            result_list.append(result)         
                else:
                    if operation == 'split_size':
                        result_list = split_by_size(file_list[0], request.form.get('size'))
                    else:
                        result_list = process_file(operation, file_list[0])
                        

                
                

                memory_file = io.BytesIO()
                with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    if operation in ('convert_vatv','clean_mt','merge_tmx'):
                        if type(result_list) == str:
                            zf.write(result_list, os.path.basename(result_list))
                        else:
                            file_path = result_list[0]
                            zf.write(file_path, os.path.basename(file_path))
                    else:
                        for result in result_list:
                            if len(result) > 2:
                                if os.path.exists(result):
                                    zf.write(result, os.path.basename(result))
                            else:
                                for tm in result:
                                    if os.path.exists(tm):
                                        zf.write(tm, os.path.basename(tm))

                memory_file.seek(0)
                # Handle different result types
                if isinstance(memory_file, io.BytesIO):
                    return send_file(
                        memory_file,
                        mimetype='application/zip',
                        as_attachment=True,
                        download_name=f'{operation}_{filename}.zip'
                    )
                else:
                    return send_file(
                        memory_file,
                        as_attachment=True,
                        download_name=f'{operation}_{filename}'
                    )
                    
            finally:
                # Clean up input file
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    logger.warning(f"Could not remove input file {filepath}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            if is_api_request():
                return jsonify({'error': f"Error processing file: {str(e)}"}), 500
            else:
                flash(f"Error processing file: {str(e)}", 'error')
                return redirect(url_for('index'))

    # GET request - render template
    return render_template('index.html', operations=OPERATIONS)

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    logger.warning("File too large error")
    if is_api_request():
        return jsonify({'error': 'File is too large. Maximum size is 1024MB.'}), 413
    else:
        flash('File is too large. Maximum size is 1024MB.', 'error')
        return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    logger.error(f"Internal server error: {e}")
    flash('An internal error occurred. Please try again later.', 'error')
    return redirect(url_for('index'))

def process_file(operation: str, filepath: str) -> str:
    """Process the uploaded file with the selected operation"""
    try:
        if operation not in OPERATIONS:
            raise ValueError(f"Unknown operation: {operation}")
        
        logger.info(f"Starting operation {operation} on file {filepath}")
        
        # Process the file
        result = OPERATIONS[operation](filepath)
        
        # If result is a string (file path), return it
        if isinstance(result, str):
            if not os.path.exists(result):
                raise FileNotFoundError(f"Operation produced no output file at {result}")
            return result
            
        # If result is a list of files, zip them
        elif isinstance(result, tuple):
            #memory_file = io.BytesIO()
            #with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            #    for file_path in result:
            #        if os.path.exists(file_path):
            #            zf.write(file_path, os.path.basename(file_path))
            #memory_file.seek(0)
            return result
            
        else:
            raise ValueError(f"Operation {operation} returned unexpected type: {type(result)}")
            
    except Exception as e:
        logger.error(f"Error processing file {filepath} with operation {operation}: {e}")
        raise

@app.route('/api/xliff_tmx_leverage', methods=['POST'])
def xliff_tmx_leverage():
    logger.info("Received request to /api/xliff_tmx_leverage")
    try:
        operation = request.form.get('operation')
        logger.info(f"Operation: {operation}")
        
        if 'file' not in request.files or 'tmx_file' not in request.files:
            logger.error("Missing required files")
            return jsonify({'error': "Both XLIFF and TMX files are required"}), 400
            
        xliff_file = request.files['file']
        tmx_file = request.files['tmx_file']
        
        logger.info(f"Received files: XLIFF={xliff_file.filename}, TMX={tmx_file.filename}")
        
        if not xliff_file.filename or not tmx_file.filename:
            logger.error("Empty file names")
            return jsonify({'error': "Both XLIFF and TMX files must be selected"}), 400
            
        # Save uploaded files
        xliff_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(xliff_file.filename))
        tmx_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(tmx_file.filename))
        
        xliff_file.save(xliff_path)
        tmx_file.save(tmx_path)
        
        try:
            # Process the files
            output_file, stats = leverage_tmx_into_xliff(tmx_path, xliff_path)
            
            # Return both the file and stats in the response
            response = make_response(send_file(
                output_file,
                as_attachment=True,
                download_name=os.path.basename(output_file),
                mimetype='application/x-xliff+xml'
            ))
            response.headers['X-Stats'] = json.dumps(stats)
            return response
            
        finally:
            # Clean up uploaded files
            for filepath in [xliff_path, tmx_path, output_file]:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    logger.warning(f"Could not remove temporary file {filepath}: {e}")
                    
    except Exception as e:
        logger.error(f"Error in xliff_tmx_leverage: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/xliff_check', methods=['POST'])
def xliff_check():
    logger.info("Received request to /api/xliff_check")
    try:
        operation = request.form.get('operation')
        logger.info(f"Operation: {operation}")
        
        if 'file' not in request.files:
            logger.error("No file provided")
            return jsonify({'error': "No file provided"}), 400
            
        file = request.files['file']
        logger.info(f"Received file: {file.filename}")
        if not file.filename:
            logger.error("No file selected")
            return jsonify({'error': "No file selected"}), 400
            
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filepath)
        
        try:
            stats = check_empty_targets(filepath)
            logger.info(f"XLIFF check completed. Stats: {stats}")
            return jsonify(stats)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
                
    except Exception as e:
        logger.error(f"Error in xliff_check: {e}")
        return jsonify({'error': str(e)}), 400

def is_api_request():
    # Checks if the request expects JSON (AJAX/fetch) or is a form POST from the browser
    return request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']

if __name__ == '__main__':
    try:
        logger.info("Starting Flask application")
        print("Starting TMX Processing Tool...")
        print("Access the tool at http://127.0.0.1:5000")
        app.run(debug=True, port=5000, host='127.0.0.1')
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        print(f"Error: {str(e)}")
        input("Press Enter to exit...") 