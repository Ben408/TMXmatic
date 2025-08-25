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
import importlib.util
import signal
import atexit

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

# Required Python libraries for scripts
REQUIRED_LIBRARIES = [
    "PythonTmx",
    "lxml", 
    "openpyxl"
]

# Optional but recommended libraries
OPTIONAL_LIBRARIES = [
    "chardet",  # For better encoding detection
    "tqdm"      # For progress bars in batch operations
]

def is_library_installed(library_name):
    """Check if a Python library is installed and can be imported"""
    try:
        importlib.util.find_spec(library_name)
        # Try to actually import the library to ensure it works
        __import__(library_name)
        return True
    except ImportError:
        return False
    except Exception as e:
        logging.warning(f"Library {library_name} found but failed to import: {e}")
        # Try to reinstall the library if it's corrupted
        logging.info(f"Attempting to reinstall corrupted library: {library_name}")
        if install_python_library(library_name):
            try:
                __import__(library_name)
                logging.info(f"Successfully reinstalled and imported {library_name}")
                return True
            except Exception as e2:
                logging.error(f"Failed to import {library_name} after reinstall: {e2}")
                return False
        return False

def install_python_library(library_name):
    """Install a Python library using pip"""
    try:
        logging.info(f"Installing {library_name}...")
        
        # Try to upgrade if already installed
        result = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", library_name], 
                              check=True, capture_output=True, text=True)
        logging.info(f"Successfully installed/upgraded {library_name}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install {library_name}: {e.stderr}")
        
        # Check if it's a network connectivity issue
        if "connection" in e.stderr.lower() or "timeout" in e.stderr.lower():
            logging.error("Network connectivity issue detected. Please check your internet connection.")
            logging.error("You may need to configure proxy settings or try again later.")
        
        # Try without upgrade flag as fallback
        try:
            logging.info(f"Retrying installation of {library_name} without upgrade...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", library_name], 
                                  check=True, capture_output=True, text=True)
            logging.info(f"Successfully installed {library_name}")
            return True
        except subprocess.CalledProcessError as e2:
            logging.error(f"Failed to install {library_name} on retry: {e2.stderr}")
            return False

def is_pip_available():
    """Check if pip is available"""
    try:
        import pip
        return True
    except ImportError:
        return False

def check_user_permissions():
    """Check if user has sufficient permissions for library installation"""
    try:
        # Try to create a temporary file in a common location
        import tempfile
        test_file = tempfile.NamedTemporaryFile(delete=False)
        test_file.close()
        os.unlink(test_file.name)
        return True
    except (OSError, PermissionError):
        return False

def check_virtual_environment():
    """Check if running in a virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if in_venv:
        logging.info("Running in virtual environment (recommended for library management)")
    else:
        logging.warning("Not running in virtual environment")
        logging.warning("Consider using a virtual environment to avoid conflicts")
    return in_venv

def check_python_version():
    """Check if Python version is compatible with required libraries"""
    import sys
    version = sys.version_info
    
    logging.info(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    # Check minimum Python version (3.7+ for most modern libraries)
    if version < (3, 7):
        logging.error("Python 3.7 or higher is required for this application")
        logging.error("Current version: {}.{}.{}".format(version.major, version.minor, version.micro))
        return False
    
    logging.info("Python version is compatible")
    return True

def check_pip_version():
    """Check if pip version is up to date"""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                              check=True, capture_output=True, text=True)
        version_line = result.stdout.strip()
        logging.info(f"pip version: {version_line}")
        
        # Extract version number
        import re
        version_match = re.search(r'pip (\d+\.\d+\.\d+)', version_line)
        if version_match:
            version_str = version_match.group(1)
            major, minor, patch = map(int, version_str.split('.'))
            
            # Check if pip is reasonably recent (10.0+)
            if major < 10:
                logging.warning("pip version is quite old. Consider upgrading with: python -m pip install --upgrade pip")
                logging.warning("This may help resolve installation issues.")
        
        return True
    except Exception as e:
        logging.warning(f"Could not check pip version: {e}")
        return False

def ensure_python_libraries():
    """Check and install all required Python libraries for scripts"""
    logging.info("=" * 60)
    logging.info("PYTHON LIBRARY DEPENDENCY CHECK")
    logging.info("=" * 60)
    logging.info("Checking required Python libraries for scripts...")
    
    # Check if pip is available
    if not is_pip_available():
        logging.error("pip is not available. Cannot install required libraries.")
        logging.error("Please install pip first or install libraries manually.")
        return False
    
    # Check user permissions
    if not check_user_permissions():
        logging.warning("Limited permissions detected. Library installation may fail.")
        logging.warning("Consider running as administrator or using virtual environment.")
    
    missing_libraries = []
    for library in REQUIRED_LIBRARIES:
        if not is_library_installed(library):
            missing_libraries.append(library)
            logging.warning(f"Required library '{library}' is not installed")
        else:
            logging.info(f"Library '{library}' is already installed")
    
    if missing_libraries:
        logging.info(f"Installing {len(missing_libraries)} missing libraries...")
        for library in missing_libraries:
            if not install_python_library(library):
                logging.error(f"Failed to install {library}. Please install manually: pip install {library}")
                return False
        
        # Verify all libraries are now installed
        still_missing = []
        for library in missing_libraries:
            if not is_library_installed(library):
                still_missing.append(library)
        
        if still_missing:
            logging.error(f"Failed to install libraries: {still_missing}")
            logging.error("Please install manually using: pip install " + " ".join(still_missing))
            logging.error("Or try: python -m pip install " + " ".join(still_missing))
            logging.error("If you encounter permission issues, try:")
            logging.error("  - Running as administrator")
            logging.error("  - Using a virtual environment")
            logging.error("  - Adding --user flag: pip install --user " + " ".join(still_missing))
            return False
        
        logging.info("All required Python libraries are now installed")
    else:
        logging.info("All required Python libraries are already installed")
    
    # Final verification and summary
    logging.info("=== Python Library Status Summary ===")
    for library in REQUIRED_LIBRARIES:
        status = "[OK] Installed" if is_library_installed(library) else "[MISSING] Missing"
        logging.info(f"  {library}: {status}")
    logging.info("=====================================")
    
    # Check for potential conflicts
    logging.info("Checking for potential package conflicts...")
    try:
        import pkg_resources
        for library in REQUIRED_LIBRARIES:
            try:
                version = pkg_resources.get_distribution(library).version
                logging.info(f"  {library} version: {version}")
            except pkg_resources.DistributionNotFound:
                logging.warning(f"  {library}: version information not available")
    except ImportError:
        logging.info("Package version checking not available")
    
    return True

def check_optional_libraries():
    """Check and optionally install recommended libraries"""
    logging.info("Checking optional but recommended libraries...")
    
    missing_optional = []
    for library in OPTIONAL_LIBRARIES:
        if not is_library_installed(library):
            missing_optional.append(library)
            logging.info(f"Optional library '{library}' is not installed")
        else:
            logging.info(f"Optional library '{library}' is already installed")
    
    if missing_optional:
        logging.info(f"Optional libraries available: {', '.join(missing_optional)}")
        logging.info("These can be installed manually with: pip install " + " ".join(missing_optional))
    
    return True

def check_react_compatibility():
    """Check for React version compatibility issues and provide guidance"""
    logging.info("Checking React compatibility...")
    
    # Check if package.json exists and read React version
    application_path = get_application_path()
    nextjs_path = os.path.join(application_path, "dist", "New_UI")
    package_json_path = os.path.join(nextjs_path, "package.json")
    
    if os.path.exists(package_json_path):
        try:
            import json
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            # Check React version
            react_version = package_data.get('dependencies', {}).get('react', 'unknown')
            logging.info(f"React version in package.json: {react_version}")
            
            # Check for react-day-picker
            has_react_day_picker = 'react-day-picker' in package_data.get('dependencies', {})
            if has_react_day_picker:
                logging.info("react-day-picker detected in dependencies")
                
                # Check if React version is 19 or higher
                if react_version.startswith('^19') or react_version.startswith('19'):
                    logging.warning("React 19 detected with react-day-picker")
                    logging.warning("react-day-picker may have compatibility issues with React 19")
                    logging.info("Using --legacy-peer-deps flag to resolve compatibility issues")
                    logging.info("Consider updating react-day-picker to a React 19 compatible version")
                    logging.info("Alternative: Use @internationalized/date or @react-aria/datepicker")
                else:
                    logging.info("React version is compatible with react-day-picker")
            
            # Check for other potential React 19 compatibility issues
            react_dom_version = package_data.get('dependencies', {}).get('react-dom', 'unknown')
            if react_dom_version.startswith('^19') or react_dom_version.startswith('19'):
                logging.info("React DOM 19 detected - checking for compatibility issues")
                logging.info("Some packages may need --legacy-peer-deps flag")
            
        except Exception as e:
            logging.warning(f"Could not read package.json for React compatibility check: {e}")
    else:
        logging.info("package.json not found, skipping React compatibility check")
    
    return True

def provide_troubleshooting_info():
    """Provide helpful troubleshooting information"""
    logging.info("=" * 60)
    logging.info("TROUBLESHOOTING INFORMATION")
    logging.info("=" * 60)
    logging.info("If you encounter issues with library installation:")
    logging.info("1. Check your internet connection")
    logging.info("2. Try running as administrator")
    logging.info("3. Use a virtual environment: python -m venv venv")
    logging.info("4. Upgrade pip: python -m pip install --upgrade pip")
    logging.info("5. Install with --user flag: pip install --user <library>")
    logging.info("6. Check firewall/proxy settings")
    logging.info("7. Try alternative package sources: pip install -i https://pypi.org/simple/ <library>")
    logging.info("=" * 60)

def provide_npm_troubleshooting_info():
    """Provide helpful troubleshooting information for npm/React issues"""
    logging.info("=" * 60)
    logging.info("NPM/REACT TROUBLESHOOTING INFORMATION")
    logging.info("=" * 60)
    logging.info("If you encounter npm/React compatibility issues:")
    logging.info("1. Clear npm cache: npm cache clean --force")
    logging.info("2. Delete node_modules and package-lock.json")
    logging.info("3. Use --legacy-peer-deps flag: npm install --legacy-peer-deps")
    logging.info("4. Set npm config: npm config set legacy-peer-deps true")
    logging.info("5. Update react-day-picker to latest version")
    logging.info("6. Check for React 19 compatible alternatives")
    logging.info("7. Use yarn instead of npm if issues persist")
    logging.info("8. Check package.json for version conflicts")
    logging.info("")
    logging.info("For react-day-picker + React 19 specifically:")
    logging.info("1. Use --legacy-peer-deps flag (already configured)")
    logging.info("2. Consider @internationalized/date as alternative")
    logging.info("3. Check react-day-picker GitHub for React 19 support")
    logging.info("4. Use npm install --force if other methods fail")
    logging.info("5. Consider downgrading to React 18 if needed")
    logging.info("=" * 60)

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
        
        # Check npm version and provide React 19 compatibility guidance
        try:
            result = subprocess.run(['npm', '--version'], check=True, capture_output=True, text=True)
            npm_version = result.stdout.strip()
            logging.info(f"npm version: {npm_version}")
            
            # Check if we need to configure npm for React 19 compatibility
            logging.info("Configuring npm for React 19 compatibility...")
            try:
                # Set legacy peer deps to handle React 19 compatibility issues
                subprocess.run(['npm', 'config', 'set', 'legacy-peer-deps', 'true'], 
                             check=True, capture_output=True, text=True)
                logging.info("npm configured with legacy-peer-deps=true for React 19 compatibility")
                
                # Additional npm configurations for React 19 compatibility
                try:
                    subprocess.run(['npm', 'config', 'set', 'strict-peer-dependencies', 'false'], 
                                 check=True, capture_output=True, text=True)
                    logging.info("npm configured with strict-peer-dependencies=false")
                except Exception:
                    pass
                    
                try:
                    subprocess.run(['npm', 'config', 'set', 'auto-install-peers', 'false'], 
                                 check=True, capture_output=True, text=True)
                    logging.info("npm configured with auto-install-peers=false")
                except Exception:
                    pass
                    
            except subprocess.CalledProcessError as e:
                logging.warning(f"Could not set npm legacy-peer-deps config: {e}")
                logging.info("Will use --legacy-peer-deps flag in npm commands instead")
        except Exception as e:
            logging.warning(f"Could not check npm version: {e}")
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
                # Use --legacy-peer-deps to handle React 19 compatibility issues
                result = subprocess.run([npm_path, 'install', '--legacy-peer-deps'], 
                                     check=True, 
                                     capture_output=True, 
                                     text=True)
                logging.info(f"npm install output: {result.stdout}")
            except subprocess.CalledProcessError as e:
                logging.error(f"npm install failed: {e.stderr}")
                logging.info("Trying npm install without legacy peer deps...")
                try:
                    result = subprocess.run([npm_path, 'install'], 
                                         check=True, 
                                         capture_output=True, 
                                         text=True)
                    logging.info(f"npm install (fallback) output: {result.stdout}")
                except subprocess.CalledProcessError as e2:
                    logging.error(f"npm install fallback also failed: {e2.stderr}")
                    logging.error("npm install failed completely. Providing troubleshooting information...")
                    provide_npm_troubleshooting_info()
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
            logging.error("Build failed. This may be due to React 19 compatibility issues.")
            provide_npm_troubleshooting_info()
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

def cleanup_processes():
    """Clean up all processes and resources when shutting down"""
    logging.info("Starting process cleanup...")
    
    # Clean up Next.js process
    try:
        if 'nextjs_process' in globals() and nextjs_process:
            logging.info(f"Terminating Next.js process (PID: {nextjs_process.pid})")
            nextjs_process.terminate()
            nextjs_process.wait(timeout=5)
            logging.info("Next.js process terminated successfully")
    except Exception as e:
        logging.warning(f"Error terminating Next.js process: {e}")
        try:
            if 'nextjs_process' in globals() and nextjs_process:
                nextjs_process.kill()
                logging.info("Force killed Next.js process")
        except Exception as e2:
            logging.warning(f"Error force killing Next.js process: {e2}")
    
    # Clean up Flask processes
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if ':5000' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        try:
                            logging.info(f"Terminating Flask process (PID: {pid})")
                            subprocess.run(['taskkill', '/PID', pid, '/F'], check=False)
                        except Exception as e:
                            logging.warning(f"Error terminating Flask process {pid}: {e}")
    except Exception as e:
        logging.warning(f"Error checking for Flask processes: {e}")
    
    # Clean up any remaining Python processes related to this launcher
    try:
        current_pid = os.getpid()
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True, check=False)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'python.exe' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = parts[1]
                        if pid.isdigit() and int(pid) != current_pid:
                            try:
                                # Check if this is a child process
                                parent_result = subprocess.run(['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 'ParentProcessId'], 
                                                            capture_output=True, text=True, check=False)
                                if str(current_pid) in parent_result.stdout:
                                    logging.info(f"Terminating child process (PID: {pid})")
                                    subprocess.run(['taskkill', '/PID', pid, '/F'], check=False)
                            except Exception as e:
                                logging.warning(f"Error checking process {pid}: {e}")
    except Exception as e:
        logging.warning(f"Error checking for child processes: {e}")
    
    # Clean up ports
    try:
        if 'nextjs_port_global' in globals() and nextjs_port_global:
            logging.info(f"Checking if port {nextjs_port_global} is still in use...")
            if not check_port_available(nextjs_port_global):
                logging.info(f"Port {nextjs_port_global} is still in use, attempting to free it...")
                # The port should be freed when the process is terminated
    except Exception as e:
        logging.warning(f"Error checking port status: {e}")
    
    # Clean up threads
    try:
        if 'flask_thread' in globals() and flask_thread and flask_thread.is_alive():
            logging.info("Flask thread is still running, it will terminate with main process")
        if 'nextjs_thread' in globals() and nextjs_thread and nextjs_thread.is_alive():
            logging.info("Next.js thread is still running, it will terminate with main process")
    except Exception as e:
        logging.warning(f"Error checking thread status: {e}")
    
    # Final cleanup - kill any remaining processes that might be using our ports
    try:
        if 'nextjs_port_global' in globals() and nextjs_port_global:
            logging.info(f"Performing final cleanup for port {nextjs_port_global}...")
            # Use netstat to find processes using our port
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if f':{nextjs_port_global}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                logging.info(f"Found process {pid} still using port {nextjs_port_global}, terminating...")
                                subprocess.run(['taskkill', '/PID', pid, '/F'], check=False)
                            except Exception as e:
                                logging.warning(f"Error terminating process {pid}: {e}")
    except Exception as e:
        logging.warning(f"Error during final port cleanup: {e}")
    
    logging.info("Process cleanup completed")

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    logging.info(f"Received signal {signum}. Shutting down gracefully...")
    cleanup_processes()
    sys.exit(0)

def windows_cleanup_handler():
    """Windows-specific cleanup handler for when console window is closed"""
    logging.info("Windows console window closing detected. Cleaning up processes...")
    cleanup_processes()

def setup_cleanup_handlers():
    """Set up various cleanup handlers for different exit scenarios"""
    # Register cleanup function to run at exit
    atexit.register(cleanup_processes)
    
    # Set up signal handlers for Unix-like systems
    try:
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    except (AttributeError, OSError):
        # Windows doesn't support SIGTERM
        pass
    
    # Windows-specific cleanup
    if os.name == 'nt':  # Windows
        try:
            import ctypes
            from ctypes import wintypes
            
            # Define Windows API constants
            CTRL_CLOSE_EVENT = 2
            
            # Define the handler function
            def windows_handler(ctrl_type):
                if ctrl_type == CTRL_CLOSE_EVENT:
                    windows_cleanup_handler()
                return True
            
            # Set the handler
            ctypes.windll.kernel32.SetConsoleCtrlHandler(
                ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)(windows_handler), 
                True
            )
        except Exception as e:
            logging.warning(f"Could not set up Windows cleanup handler: {e}")

def check_port_available(port):
    """Check if a port is available"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False

def main():
    try:
        setup_logging()
        logging.info("Starting TMXmatic application...")
        
        # Set up cleanup handlers for graceful shutdown
        setup_cleanup_handlers()
        
        # Initialize global process variables
        global nextjs_process, nextjs_port_global
        nextjs_process = None
        nextjs_port_global = 3000 # Default to 3000
        
        # Check Python version compatibility
        if not check_python_version():
            logging.error("Python version check failed. Exiting.")
            logging.error("Please upgrade to Python 3.7 or higher")
            sys.exit(1)
        
        # Check pip version
        check_pip_version()
        
        # Check virtual environment status
        check_virtual_environment()
        
        # Ensure required Python libraries are installed
        if not ensure_python_libraries():
            logging.error("Failed to install required Python libraries. Exiting.")
            provide_troubleshooting_info()
            sys.exit(1)
        
        # Check optional libraries (informational only)
        check_optional_libraries()
        
        # Check React compatibility
        check_react_compatibility()
        
        # Summary of all checks
        logging.info("=" * 60)
        logging.info("ALL DEPENDENCY CHECKS COMPLETED SUCCESSFULLY")
        logging.info("=" * 60)

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
        cleanup_processes()
        sys.exit(0)
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        logging.error("Performing emergency cleanup...")
        try:
            cleanup_processes()
        except Exception as cleanup_error:
            logging.error(f"Error during emergency cleanup: {cleanup_error}")
        sys.exit(1)
    finally:
        # Ensure cleanup happens even if we exit normally
        logging.info("Main function exiting, performing final cleanup...")
        try:
            cleanup_processes()
        except Exception as cleanup_error:
            logging.error(f"Error during final cleanup: {cleanup_error}")

if __name__ == '__main__':
    main() 