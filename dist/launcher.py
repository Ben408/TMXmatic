import os
import sys
import subprocess
import webbrowser
from threading import Thread
import time
import shutil
import urllib.request
import tempfile
import logging
from datetime import datetime

# Set up logging to both file and console
def setup_logging():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    log_file = os.path.join(application_path, f'tmxmatic_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Configure logging to write to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info(f"Log file created at: {log_file}")

def get_application_path():
    """Get the base application path, handling both development and frozen environments."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

NODE_DOWNLOAD_URL = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi"  # LTS version as of June 2024

def is_tool(name):
    """Check whether `name` is on PATH and marked as executable."""
    return shutil.which(name) is not None

def install_node():
    logging.info("Node.js and npm not found. Downloading and installing Node.js...")
    with tempfile.TemporaryDirectory() as tmpdirname:
        installer_path = os.path.join(tmpdirname, "node_installer.msi")
        logging.info(f"Downloading Node.js installer from {NODE_DOWNLOAD_URL}...")
        urllib.request.urlretrieve(NODE_DOWNLOAD_URL, installer_path)
        logging.info("Running Node.js installer (silent mode)...")
        result = subprocess.run(["msiexec", "/i", installer_path, "/quiet", "/norestart"], check=False)
        if result.returncode == 0:
            logging.info("Node.js installed successfully.")
        else:
            logging.error("Node.js installation failed. Please install manually.")
            sys.exit(1)

def ensure_node_npm():
    node_installed = is_tool("node")
    npm_installed = is_tool("npm")
    if node_installed and npm_installed:
        logging.info("Node.js and npm are already installed.")
    else:
        install_node()
        if is_tool("node") and is_tool("npm"):
            logging.info("Node.js and npm are now installed.")
        else:
            logging.error("Node.js and npm installation failed. Please install manually.")
            sys.exit(1)

def run_flask():
    application_path = get_application_path()
    os.chdir(application_path)
    from app import app
    app.run(port=5000)

def run_nextjs():
    try:
        ensure_node_npm()
        application_path = get_application_path()
        
        # In frozen environment, Next.js files are in the same directory as the executable
        nextjs_path = os.path.join(application_path, 'New_UI')
        logging.info(f"Next.js path: {nextjs_path}")
        
        if not os.path.exists(nextjs_path):
            logging.error(f"Next.js directory not found at: {nextjs_path}")
            logging.error(f"Current directory contents: {os.listdir(application_path)}")
            return
        
        os.chdir(nextjs_path)
        
        # Get the full path to npm
        npm_path = shutil.which('npm')
        if not npm_path:
            logging.error("npm not found in PATH")
            return
        logging.info(f"Using npm from: {npm_path}")
        
        # First, install dependencies if node_modules doesn't exist
        if not os.path.exists(os.path.join(nextjs_path, 'node_modules')):
            logging.info("Installing Next.js dependencies...")
            try:
                result = subprocess.run([npm_path, 'install'], 
                                     check=True, 
                                     capture_output=True, 
                                     text=True)
                logging.info(f"npm install output: {result.stdout}")
            except subprocess.CalledProcessError as e:
                logging.error(f"npm install failed: {e.stderr}")
                return
        
        # Then start the Next.js server
        logging.info("Starting Next.js server...")
        try:
            process = subprocess.Popen(
                [npm_path, 'run', 'start'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Wait a bit and check if the process is still running
            time.sleep(5)
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logging.error(f"Next.js server failed to start. Error: {stderr}")
                logging.error(f"Next.js server output: {stdout}")
                return
                
            logging.info("Next.js server started successfully")
            
        except Exception as e:
            logging.error(f"Error starting Next.js server process: {str(e)}")
            return
            
    except Exception as e:
        logging.error(f"Error starting Next.js server: {str(e)}")
        return

def main():
    try:
        setup_logging()
        logging.info("Starting TMXmatic application...")
        
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        nextjs_thread = Thread(target=run_nextjs)
        nextjs_thread.daemon = True
        nextjs_thread.start()
        
        # Wait longer for servers to start
        time.sleep(10)
        
        logging.info("Opening browser...")
        webbrowser.open('http://localhost:3000')
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 