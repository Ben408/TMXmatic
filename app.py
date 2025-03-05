from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
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

print(f"Looking for PythonTmx at: {pythontmx_path}")  # Debug print
print(f"Directory exists: {os.path.exists(pythontmx_path)}")  # Debug print

if tmx_path not in sys.path:
    sys.path.insert(0, tmx_path)
if pythontmx_path not in sys.path:
    sys.path.insert(0, pythontmx_path)

try:
    import PythonTmx
    print("Successfully imported PythonTmx")  # Debug print
except ImportError as e:
    print(f"Failed to import PythonTmx from {pythontmx_path}")
    print(f"Current sys.path: {sys.path}")
    print(f"Directory contents: {os.listdir(tmx_path)}")  # Debug print
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

# Application Configuration
app.config.update(
    UPLOAD_FOLDER=os.path.join(application_path, 'uploads'),
    MAX_CONTENT_LENGTH=512 * 1024 * 1024,  # 512MB max file size
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

# Update the operations mapping to match the imported function names
OPERATIONS = {
    'remove_old': remove_old_tus,
    'empty_targets': empty_targets,
    'true_duplicates': find_true_duplicates,
    'non_true_duplicates': extract_non_true_duplicates,
    'sentence_level': find_sentence_level_segments,
    'convert_vatv': convert_vatv_to_tmx,
    'convert_termweb': convert_termweb_to_tmx,
    'count_creation': count_creation_dates,
    'count_usage': count_last_usage_dates,
    'extract_translations': extract_translations,
    'split_language': split_by_language,
    'split_size': split_by_size,
    'batch_process': batch_process_1_5
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Add error handling and logging
        try:
            file = request.files['file']
            if file and file.filename:
                operation = request.form.get('operation')
                # Add logging
                app.logger.info(f"Processing file: {file.filename} with operation: {operation}")
                
                # Save file to temp location
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Process file
                result_file = process_file(operation, filepath)
                
                return send_file(
                    result_file,
                    as_attachment=True,
                    download_name=f'processed_{filename}'
                )
        except Exception as e:
            app.logger.error(f"Error processing file: {str(e)}")
            flash(f"Error processing file: {str(e)}", 'error')
            return redirect(url_for('index'))
            
        finally:
            # Clean up working directory
            try:
                if upload_dir.exists():
                    shutil.rmtree(upload_dir)
                    logger.info(f"Cleaned up working directory: {upload_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up directory {upload_dir}: {e}")

    # For GET requests, render the template with operations list
    operations = {
        'convert_vatv': 'Convert VATV CSV',
        'convert_termweb': 'Convert TermWeb Excel',
        'remove_empty': 'Remove Empty Targets',
        'find_duplicates': 'Find True Duplicates',
        'non_true_duplicates': 'Find Non-True Duplicates',
        'clean_mt': 'Clean TMX for MT',
        'merge_tmx': 'Merge TMX Files',
        'split_language': 'Split TMX by Language',
        'split_size': 'Split TMX by Size',
        'batch_process_tms': 'Batch Clean TMX for TMS',
        'batch_process_mt': 'Batch Clean TMX for MT'
    }
    
    return render_template('index.html', operations=operations)

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    logger.warning("File too large error")
    flash('File is too large. Maximum size is 512MB.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    logger.error(f"Internal server error: {e}")
    flash('An internal error occurred. Please try again later.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    try:
        logger.info("Starting Flask application")
        print("Starting TMX Processing Tool...")
        print("Access the tool at http://localhost:5000")
        app.run(debug=False, port=5000, host='127.0.0.1')
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        print(f"Error: {str(e)}")
        input("Press Enter to exit...") 