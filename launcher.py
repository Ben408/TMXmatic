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

def check_port_available(port):
    """Check if a port is available"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False

def get_process_using_port(port):
    """Get information about what process is using a specific port"""
    try:
        import subprocess
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        # Try to get process name
                        task_result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                                   capture_output=True, text=True)
                        task_lines = task_result.stdout.split('\n')
                        for task_line in task_lines:
                            if pid in task_line:
                                return f"PID {pid}: {task_line.strip()}"
                    except:
                        pass
                    return f"PID {pid}"
        return "Unknown process"
    except Exception as e:
        return f"Error checking process: {str(e)}"

def check_server_running(url, timeout=5):
    """Check if a server is running and accessible"""
    import urllib.request
    try:
        response = urllib.request.urlopen(url, timeout=timeout)
        return response.getcode() == 200
    except:
        return False

def monitor_process_output(process, process_name):
    """Monitor process output in real-time"""
    def monitor():
        while True:
            if process.poll() is not None:
                break
            output = process.stdout.readline()
            if output:
                output_text = output.strip()
                logging.info(f"{process_name}: {output_text}")
                
                # Try to detect port from Next.js output
                if "Local:" in output_text and "localhost:" in output_text:
                    import re
                    port_match = re.search(r'localhost:(\d+)', output_text)
                    if port_match:
                        global nextjs_port_global
                        detected_port = int(port_match.group(1))
                        if nextjs_port_global != detected_port:
                            nextjs_port_global = detected_port
                            logging.info(f"Detected Next.js port from output: {detected_port}")
                
            error = process.stderr.readline()
            if error:
                logging.error(f"{process_name} ERROR: {error.strip()}")
            time.sleep(0.1)
    
    monitor_thread = Thread(target=monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    return monitor_thread

def run_nextjs():
    try:
        ensure_node_npm()
        application_path = get_application_path()
        
        # In frozen environment, Next.js files are in the same directory as the executable
        nextjs_path = os.path.join(application_path, "dist", "New_UI")
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
        
        # Build the Next.js application
        logging.info("Building Next.js application...")
        try:
            result = subprocess.run([npm_path, 'run', 'build'], 
                                 check=True, 
                                 capture_output=True, 
                                 text=True)
            logging.info("Next.js build completed successfully")
        except subprocess.CalledProcessError as e:
            logging.error(f"Next.js build failed: {e.stderr}")
            logging.error(f"Build output: {e.stdout}")
            return
        
        # Verify build output exists
        next_build_dir = os.path.join(nextjs_path, '.next')
        if not os.path.exists(next_build_dir):
            logging.error("Next.js build output directory '.next' not found after build")
            return
        
        logging.info("Next.js build verification completed")
        
        # Check if port 3000 is available
        nextjs_port = 3000
        if not check_port_available(3000):
            process_info = get_process_using_port(3000)
            logging.warning(f"Port 3000 is already in use by: {process_info}")
            logging.warning("Next.js will automatically choose an available port.")
            nextjs_port = None  # Let Next.js choose automatically
        
        # Then start the Next.js server
        logging.info(f"Starting Next.js server...")
        try:
            dev_command = [npm_path, 'run', 'dev']
            
            logging.info(f"Running command: {' '.join(dev_command)}")
            process = subprocess.Popen(
                dev_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Start monitoring the process output
            monitor_thread = monitor_process_output(process, "Next.js")
            
            # Wait for Next.js to start and detect the port
            logging.info("Waiting for Next.js to start and detect port...")
            max_wait_time = 30
            wait_time = 0
            detected_port = None
            
            while wait_time < max_wait_time and detected_port is None:
                time.sleep(1)
                wait_time += 1
                
                # Check if process is still running
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    logging.error(f"Next.js server failed to start. Error: {stderr}")
                    logging.error(f"Next.js server output: {stdout}")
                    logging.error(f"Process return code: {process.returncode}")
                    return
                
                # Try to detect the port from the output
                if nextjs_port is None:
                    # Check common ports
                    for port in range[3000, 3010]:
                        if check_server_running(f'http://localhost:{port}'):
                            detected_port = port
                            logging.info(f"Detected Next.js running on port {detected_port}")
                            break
            
            if detected_port is None:
                logging.error("Failed to detect Next.js port within timeout")
                return
            
            nextjs_port = detected_port
            logging.info(f"Next.js server started successfully on port {nextjs_port}")
            logging.info(f"Process ID: {process.pid}")
            
            # Store the process for potential cleanup later
            global nextjs_process, nextjs_port_global
            nextjs_process = process
            nextjs_port_global = nextjs_port
            
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
        
        # Initialize global process variables
        global nextjs_process, nextjs_port_global
        nextjs_process = None
        nextjs_port_global = 3000 # Default to 3000
        
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        nextjs_thread = Thread(target=run_nextjs)
        nextjs_thread.daemon = True
        nextjs_thread.start()
        
        # Wait longer for servers to start
        time.sleep(10)
        
        # Wait for Next.js server to be accessible
        logging.info("Waiting for Next.js server to be ready...")
        max_wait_time = 10  # Wait up to 10 seconds
        wait_time = 0
        while wait_time < max_wait_time:
            if check_server_running(f'http://localhost:{nextjs_port_global}'):
                logging.info("Next.js server is ready!")
                break
            if check_server_running(f'http://localhost:{nextjs_port_global + 1}'):
                logging.info("Next.js server is ready!")
                nextjs_port_global = nextjs_port_global + 1
                break
            if check_server_running(f'http://localhost:{nextjs_port_global + 2}'):
                logging.info("Next.js server is ready!")
                nextjs_port_global = nextjs_port_global + 2
                break
            if check_server_running(f'http://localhost:{nextjs_port_global + 3}'):
                logging.info("Next.js server is ready!")
                nextjs_port_global = nextjs_port_global + 3
                break

            time.sleep(2)
            wait_time += 2
            logging.info(f"Waiting for Next.js server... ({wait_time}s)")
        
        if wait_time >= max_wait_time:
            logging.error("Next.js server failed to start within timeout period")
            logging.info(f"Please check the logs for errors and manually navigate to: http://localhost:{nextjs_port_global}")
        else:
            logging.info("Opening browser to Next.js application...")
            try:
                webbrowser.open(f'http://localhost:{nextjs_port_global}')
                logging.info("Browser opened successfully")
            except Exception as e:
                logging.error(f"Failed to open browser: {str(e)}")
                logging.info("Please manually navigate to: http://localhost:3000")
        
        logging.info("Application started successfully!")
        logging.info("Flask backend running on: http://localhost:5000")
        logging.info(f"Next.js frontend running on: http://localhost:{nextjs_port_global}")
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        # Clean up processes
        if 'nextjs_process' in globals() and nextjs_process:
            try:
                nextjs_process.terminate()
                logging.info("Next.js process terminated")
            except:
                pass
        sys.exit(0)
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 