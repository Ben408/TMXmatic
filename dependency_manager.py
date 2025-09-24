import os
import json
import subprocess
import logging
from typing import List, Dict, Optional

class DependencyManager:
    def __init__(self, app_path: str):
        self.app_path = app_path
        self.nextjs_path = os.path.join(app_path, "dist", "New_UI")
        self.package_json_path = os.path.join(self.nextjs_path, "package.json")
        
    def get_current_dependencies(self) -> Dict:
        """Read current package.json dependencies"""
        if os.path.exists(self.package_json_path):
            with open(self.package_json_path, 'r') as f:
                return json.load(f)
        return {}
    
    def is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed in node_modules"""
        package_path = os.path.join(self.nextjs_path, "node_modules", package_name)
        return os.path.exists(package_path)
    
    def install_package(self, package_name: str, is_dev: bool = False) -> bool:
        import shutil
        
        # Find npm executable
        npm_path = shutil.which('npm')
        if not npm_path:
            logging.error("npm not found in PATH")
            return False
            
        env = os.environ.copy()
        env.setdefault("NPM_CONFIG_FUND", "false")
        env.setdefault("NPM_CONFIG_AUDIT", "false")
        base = [npm_path, "install", "--no-progress", "--prefer-offline", "--no-audit", "--include=prod", "--legacy-peer-deps"]
        if is_dev:
            base.append("--save-dev")
        base.append(package_name)
        try:
            res = subprocess.run(base, cwd=self.nextjs_path, env=env, capture_output=True, text=True, check=True, timeout=1800)
            logging.info("Installed %s", package_name)
            return True
        except subprocess.CalledProcessError as e:
            logging.error("Failed to install %s: %s", package_name, e.stderr[-2000:])
            return False
        
class DependencyCategories:
    # Core runtime dependencies (must be pre-installed)
    CORE_RUNTIME = [
        "react",
        "react-dom", 
        "@radix-ui/react-slot",
        "@radix-ui/react-dialog",
        "@radix-ui/react-popover",
        "@radix-ui/react-tabs",
        "@radix-ui/react-toast",
        "@radix-ui/react-tooltip",
        "@radix-ui/react-scroll-area",
        "@radix-ui/react-select",
        "@radix-ui/react-label",
        "@radix-ui/react-checkbox",
        "@radix-ui/react-dropdown-menu",
        "lucide-react",
        "date-fns",
        "react-day-picker",
        "jszip",
        "react-hook-form",
        "@hookform/resolvers",
        "zod",
        "react-resizable-panels",
        "next-themes",
        "sonner",
        "class-variance-authority",
        "clsx",
        "tailwind-merge",
        "tailwindcss-animate"
    ]
    
    # Build tools (installed on first build)
    BUILD_TOOLS = [
        "next",
        "typescript",
        "@types/node",
        "@types/react", 
        "@types/react-dom",
        "@types/jszip",
        "tailwindcss",
        "postcss",
        "autoprefixer"
    ]
    
    # Optional features (installed when needed)
    OPTIONAL_FEATURES = {
        "charts": ["recharts"],
        "carousel": ["embla-carousel-react"],
        "otp": ["input-otp"],
        "drawer": ["vaul"],
        "command-palette": ["cmdk"]
    }
    
    # Unused dependencies (can be removed)
    UNUSED = [
        "embla-carousel-react",
        "input-otp", 
        "recharts",
        "vaul",
        "cmdk",
        "@radix-ui/react-accordion",
        "@radix-ui/react-aspect-ratio",
        "@radix-ui/react-collapsible",
        "@radix-ui/react-context-menu",
        "@radix-ui/react-hover-card",
        "@radix-ui/react-menubar",
        "@radix-ui/react-navigation-menu",
        "@radix-ui/react-progress",
        "@radix-ui/react-radio-group",
        "@radix-ui/react-separator",
        "@radix-ui/react-slider",
        "@radix-ui/react-switch",
        "@radix-ui/react-toggle",
        "@radix-ui/react-toggle-group"
    ]

