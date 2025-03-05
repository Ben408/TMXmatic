import sys
import os

# Add the path to your PythonTmx package
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmx', 'Lib', 'site-packages'))

import PythonTmx

print("Successfully imported PythonTmx")
print("Version:", PythonTmx.__version__ if hasattr(PythonTmx, '__version__') else "Unknown") 