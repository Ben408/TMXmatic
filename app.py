from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session, jsonify, make_response
from flask_cors import CORS
import os
import sys
import logging
from datetime import datetime
import zipfile
import io
import json
from werkzeug.utils import secure_filename
import secrets
from pathlib import Path
import shutil

# CRITICAL: Make Flask completely self-contained and path-independent
# Get the directory where THIS Flask app is running
current_app_dir = os.path.dirname(os.path.abspath(__file__))

# Add the scripts directory relative to THIS Flask app
scripts_dir = os.path.join(current_app_dir, 'scripts')
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# Add the current app directory to Python path (for relative imports)
if current_app_dir not in sys.path:
    sys.path.insert(0, current_app_dir)
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

# Import PythonTmx from the current environment (not hardcoded paths)
try:
    import PythonTmx
    logger.info("Successfully imported PythonTmx from current environment")
except ImportError as e:
    logger.critical(f"Failed to import PythonTmx: {e}")
    logger.critical("Make sure PythonTmx is installed in the current virtual environment")
    raise

# Import all script functions from the current scripts directory
try:
    # Core TMX operations
    from scripts.remove_empty import empty_targets
    from scripts.remove_duplicates import find_true_duplicates
    from scripts.remove_old import remove_old_tus
    from scripts.remove_sentence import find_sentence_level_segments
    from scripts.remove_context_props import remove_context_props_from_file
    
    # Conversion operations
    from scripts.convert_vatv import process_csv_file as convert_vatv_to_tmx
    from scripts.convert_termweb import process_excel_file as convert_termweb_to_tmx
    
    # Processing operations
    from scripts.clean_tmx_for_mt import clean_tmx_for_mt
    from scripts.batch_process import batch_process_1_5, batch_process_1_5_9
    from scripts.merge_tmx import merge_tmx_files
    from scripts.split_tmx import split_by_language, split_by_size
    
    # Analysis operations
    from scripts.extract_ntds import extract_non_true_duplicates
    from scripts.extract_translations import extract_translations
    from scripts.count_creation_dates import count_creation_dates
    from scripts.count_last_usage import count_last_usage_dates
    from scripts.find_date_duplicates import process_file as find_date_duplicates
    
    # XLIFF operations
    from scripts.xliff_operations import leverage_tmx_into_xliff, check_empty_targets
    from scripts.xliff_to_tmx import xliff_to_tmx
    from scripts.tmx_to_xliff import tmx_to_xliff
    
    # TBX operations
    from scripts.tbx_cleaner import process_tbx
    logger.info("Successfully imported all script modules from current scripts directory")
    
except ImportError as e:
    logger.critical(f"Failed to import script modules: {e}")
    logger.critical(f"Current scripts directory: {scripts_dir}")
    logger.critical(f"Python path: {sys.path}")
    raise

# Flask app initialization - completely self-contained
if getattr(sys, 'frozen', False):
    # For compiled/packaged versions
    application_path = os.path.dirname(sys.executable)
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    app = Flask(__name__, 
                template_folder=template_folder,
                static_folder=os.path.join(template_folder, 'static'))
else:
    # For development - use current directory
    application_path = current_app_dir
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Application Configuration - all paths relative to current app directory
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

# Log startup information for debugging
logger.info("=" * 80)
logger.info("FLASK APP STARTUP")
logger.info("=" * 80)
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Flask app directory: {current_app_dir}")
logger.info(f"Scripts directory: {scripts_dir}")
logger.info(f"Upload directory: {app.config['UPLOAD_FOLDER']}")
logger.info(f"Python path: {sys.path[:3]}...")  # Show first 3 entries
logger.info("=" * 80)

def verify_import_locations():
    """Verify that all imported functions are from the correct scripts directory"""
    logger.info("VERIFYING IMPORT LOCATIONS:")
    
    # Check key functions
    functions_to_check = [
        ('empty_targets', empty_targets),
        ('find_true_duplicates', find_true_duplicates),
        ('remove_old_tus', remove_old_tus),
        ('clean_tmx_for_mt', clean_tmx_for_mt),
        ('merge_tmx_files', merge_tmx_files),
        ('split_by_language', split_by_language),
    ]
    
    for func_name, func in functions_to_check:
        try:
            func_file = func.__code__.co_filename
            if scripts_dir in func_file:
                logger.info(f"[OK] {func_name}: {func_file}")
            else:
                logger.warning(f"[WARN] {func_name}: {func_file} (NOT from current scripts directory!)")
        except Exception as e:
            logger.warning(f"[WARN] {func_name}: Could not verify location - {e}")
    
    logger.info("=" * 80)

# Verify imports on startup
verify_import_locations()

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
    ALLOWED_EXTENSIONS = {'tmx', 'csv', 'xlsx', 'xls', 'zip', 'tbx', 'xlf', 'xliff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_xliff_to_tmx_if_needed(filepath):
    """Convert XLIFF file to TMX if the file is an XLIFF file, otherwise return original path"""
    if not os.path.exists(filepath):
        return filepath
    
    # Check if file is XLIFF by extension
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ['.xlf', '.xliff']:
        try:
            logger.info(f"Converting XLIFF file to TMX: {filepath}")
            tmx_path, _ = xliff_to_tmx(filepath)
            # Remove original XLIFF file after conversion
            try:
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"Could not remove XLIFF file {filepath}: {e}")
            return tmx_path
        except Exception as e:
            logger.error(f"Error converting XLIFF to TMX: {e}")
            raise
    return filepath

def convert_tmx_to_xliff_if_needed(filepath):
    """Convert TMX file back to XLIFF if it was originally an XLIFF file, otherwise return original path"""
    if not os.path.exists(filepath):
        return filepath
    
    # Check if file is TMX by extension
    ext = os.path.splitext(filepath)[1].lower()
    if ext != '.tmx':
        return filepath
    
    try:
        # Try to check if TMX contains XLIFF version metadata
        import PythonTmx
        tmx = PythonTmx.Tmx(filepath)
        
        # Check header notes for original XLIFF version
        xliff_version = None
        for note in tmx.header.notes:
            note_text = None
            if hasattr(note, 'content') and note.content:
                note_text = note.content
            elif hasattr(note, 'text') and note.text:
                note_text = note.text
            
            if note_text and 'Original XLIFF version' in note_text:
                # Extract version from note text
                version = note_text.split(':')[-1].strip()
                if version in ['1.2', '2.0', '2.2']:
                    xliff_version = version
                    break
        
        # If we found XLIFF version metadata, convert back to XLIFF
        if xliff_version:
            logger.info(f"Converting TMX file back to XLIFF {xliff_version}: {filepath}")
            # Generate output filename with .xlf extension
            base_path = os.path.splitext(filepath)[0]
            xliff_path = f"{base_path}.xlf"
            tmx_to_xliff(filepath, xliff_path, xliff_version)
            # Remove original TMX file after conversion
            try:
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"Could not remove TMX file {filepath}: {e}")
            return xliff_path
    except Exception as e:
        # If we can't determine or convert, just return original file
        logger.debug(f"Could not convert TMX to XLIFF (file may not be from XLIFF): {e}")
        pass
    
    return filepath

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

# Special wrapper functions for operations needing different parameters
def merge_tmx_wrapper(filepath):
    """Wrapper for merge_tmx that converts single file to list for UI compatibility"""
    # For UI compatibility, when called with single file, merge with itself
    # In practice, UI should handle this differently for multiple files
    return merge_tmx_files([filepath])

def split_size_wrapper(filepath, max_tus=50000):
    """Wrapper for split_by_size with default max_tus"""
    return split_by_size(filepath, max_tus)

def xliff_leverage_wrapper(xliff_filepath, tmx_filepath=None):
    """Wrapper for XLIFF leveraging operations"""
    if tmx_filepath is None:
        raise ValueError("TMX file required for XLIFF leveraging")
    return leverage_tmx_into_xliff(tmx_filepath, xliff_filepath)

# Update OPERATIONS to use the decorator - ALL 21 SCRIPTS
OPERATIONS = {
    # File conversion operations
    'convert_vatv': handle_tmx_operation(convert_vatv_to_tmx),
    'convert_termweb': handle_tmx_operation(convert_termweb_to_tmx),
    
    # Core TMX cleaning operations
    'remove_empty': handle_tmx_operation(empty_targets),
    'find_duplicates': handle_tmx_operation(find_true_duplicates),
    'non_true_duplicates': handle_tmx_operation(extract_non_true_duplicates),
    'remove_sentence': handle_tmx_operation(find_sentence_level_segments),
    'remove_old': handle_tmx_operation(remove_old_tus),
    'clean_mt': handle_tmx_operation(clean_tmx_for_mt),
    
    # Analysis operations
    'count_last_usage': handle_tmx_operation(count_last_usage_dates),
    'count_creation_dates': handle_tmx_operation(count_creation_dates),
    'extract_translations': handle_tmx_operation(extract_translations),
    'find_date_duplicates': handle_tmx_operation(find_date_duplicates),
    'remove_context_props': handle_tmx_operation(remove_context_props_from_file),
    
    # File manipulation operations
    'merge_tmx': handle_tmx_operation(merge_tmx_wrapper),  # Uses wrapper for UI compatibility
    'split_language': handle_tmx_operation(split_by_language),
    'split_size': handle_tmx_operation(split_size_wrapper),  # Uses wrapper with default size
    
    # Batch operations
    'batch_process_tms': handle_tmx_operation(batch_process_1_5),
    'batch_process_mt': handle_tmx_operation(batch_process_1_5_9),

    # TBX operations
    'process_tbx': handle_tmx_operation(process_tbx),
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
                file.save(filepath)
                # Convert XLIFF to TMX if needed
                converted_path = convert_xliff_to_tmx_if_needed(filepath)
                file_list.append(converted_path)

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
                            # Convert TMX back to XLIFF if it was originally XLIFF
                            file_to_add = convert_tmx_to_xliff_if_needed(result_list)
                            zf.write(file_to_add, os.path.basename(file_to_add))
                        else:
                            file_path = result_list[0]
                            # Convert TMX back to XLIFF if it was originally XLIFF
                            file_to_add = convert_tmx_to_xliff_if_needed(file_path)
                            zf.write(file_to_add, os.path.basename(file_to_add))
                    else:
                        for result in result_list:
                            if len(result) > 2:
                                if os.path.exists(result):
                                    # Convert TMX back to XLIFF if it was originally XLIFF
                                    file_to_add = convert_tmx_to_xliff_if_needed(result)
                                    zf.write(file_to_add, os.path.basename(file_to_add))
                            else:
                                for tm in result:
                                    if os.path.exists(tm):
                                        # Convert TMX back to XLIFF if it was originally XLIFF
                                        file_to_add = convert_tmx_to_xliff_if_needed(tm)
                                        zf.write(file_to_add, os.path.basename(file_to_add))




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
                file.save(filepath)
                # Convert XLIFF to TMX if needed
                if operation not in ('clean_xliff', 'validate_xliff'):
                    converted_path = convert_xliff_to_tmx_if_needed(filepath)
                    file_list.append(converted_path)
                else:
                    file_list.append(filepath)
                
            try:
                result_list = None
                if len(file_list) > 1:
                    if operation == 'merge_tmx':
                        result_list = merge_tmx_files(file_list)
                    elif operation == 'split_size':
                        result_list = split_by_size(file_list, request.form.get('size'))
                    else:
                        result_list = []
                        for file in file_list:
                            # Get cutoff_date if available
                            cutoff_date = request.form.get('cutoff_date')
                            if cutoff_date and operation in ['remove_old', 'find_date_duplicates']:
                                result = process_file(operation, file, cutoff_date=cutoff_date)
                            else:
                                result = process_file(operation, file)
                            result_list.append(result)         
                else:
                    if operation == 'split_size':
                        result_list = split_by_size(file_list[0], request.form.get('size'))
                    elif operation == 'split_language':
                        result_list = split_by_language(file_list[0])
                    else:
                        # Get cutoff_date if available
                        cutoff_date = request.form.get('cutoff_date')
                        if cutoff_date and operation in ['remove_old', 'find_date_duplicates']:
                            result_list = process_file(operation, file_list[0], cutoff_date=cutoff_date)
                        else:
                            result_list = process_file(operation, file_list[0])
                        
                
                
                

                memory_file = io.BytesIO()
                with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    if operation in ('convert_vatv','clean_mt','merge_tmx'):
                        if type(result_list) == str:
                            # Convert TMX back to XLIFF if it was originally XLIFF
                            file_to_add = convert_tmx_to_xliff_if_needed(result_list)
                            zf.write(file_to_add, os.path.basename(file_to_add))
                        else:
                            file_path = result_list[0]
                            # Convert TMX back to XLIFF if it was originally XLIFF
                            file_to_add = convert_tmx_to_xliff_if_needed(file_path)
                            zf.write(file_to_add, os.path.basename(file_to_add))
                    else:
                        print(result_list)
                        for result in result_list:
                            if len(result) > 2:
                                if os.path.exists(result):
                                    # Convert TMX back to XLIFF if it was originally XLIFF
                                    file_to_add = convert_tmx_to_xliff_if_needed(result)
                                    zf.write(file_to_add, os.path.basename(file_to_add))
                            else:
                                for tm in result:
                                    if os.path.exists(tm):
                                        # Convert TMX back to XLIFF if it was originally XLIFF
                                        file_to_add = convert_tmx_to_xliff_if_needed(tm)
                                        zf.write(file_to_add, os.path.basename(file_to_add))

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

def process_file(operation: str, filepath: str, **kwargs) -> str:
    """Process the uploaded file with the selected operation"""
    try:
        if operation not in OPERATIONS:
            raise ValueError(f"Unknown operation: {operation}")
        
        logger.info(f"Starting operation {operation} on file {filepath}")
        
        # Process the file
        if operation == 'remove_old' and 'cutoff_date' in kwargs:
            result = OPERATIONS[operation](filepath, kwargs['cutoff_date'])
        elif operation == 'find_date_duplicates' and 'cutoff_date' in kwargs:
            result = OPERATIONS[operation](filepath, kwargs['cutoff_date'])
        else:
            result = OPERATIONS[operation](filepath)
        
        # If result is a string (file path), return it
        if isinstance(result, str):
            if not os.path.exists(result):
                raise FileNotFoundError(f"Operation produced no output file at {result}")
            return result
            
        # If result is a list of files, zip them
        elif isinstance(result, tuple):
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