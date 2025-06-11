import subprocess
import shutil
import os
import sys
import urllib.request
import tempfile

NODE_DOWNLOAD_URL = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi"  # LTS version as of June 2024


def is_tool(name):
    """Check whether `name` is on PATH and marked as executable."""
    return shutil.which(name) is not None


def install_node():
    print("Node.js and npm not found. Downloading and installing Node.js...")
    with tempfile.TemporaryDirectory() as tmpdirname:
        installer_path = os.path.join(tmpdirname, "node_installer.msi")
        print(f"Downloading Node.js installer from {NODE_DOWNLOAD_URL}...")
        urllib.request.urlretrieve(NODE_DOWNLOAD_URL, installer_path)
        print("Running Node.js installer (silent mode)...")
        # /quiet for silent install
        result = subprocess.run(["msiexec", "/i", installer_path, "/quiet", "/norestart"], check=False)
        if result.returncode == 0:
            print("Node.js installed successfully.")
        else:
            print("Node.js installation failed. Please install manually.")
            sys.exit(1)


def main():
    node_installed = is_tool("node")
    npm_installed = is_tool("npm")

    if node_installed and npm_installed:
        print("Node.js and npm are already installed.")
    else:
        install_node()
        # After install, check again
        if is_tool("node") and is_tool("npm"):
            print("Node.js and npm are now installed.")
        else:
            print("Node.js and npm installation failed. Please install manually.")
            sys.exit(1)

if __name__ == "__main__":
    main() 