import os
import json
import subprocess
import logging
import shutil
from typing import List, Dict, Set

class DependencyManager:
    def __init__(self, app_path: str):
        self.app_path = app_path
        self.nextjs_path = os.path.join(app_path, "dist", "New_UI")
        self.package_json_path = os.path.join(self.nextjs_path, "package.json")
        self.package_lock_path = os.path.join(self.nextjs_path, "package-lock.json")
        
    def get_current_dependencies(self) -> Dict:
        """Read current package.json dependencies"""
        if os.path.exists(self.package_json_path):
            with open(self.package_json_path, 'r') as f:
                return json.load(f)
        return {}

    def get_declared_package_names(self) -> List[str]:
        """Top-level package names from package.json (dependencies + devDependencies)."""
        data = self.get_current_dependencies()
        names: List[str] = []
        for key in ("dependencies", "devDependencies"):
            block = data.get(key) or {}
            if isinstance(block, dict):
                names.extend(block.keys())
        # Stable order: preserve declaration order while deduplicating
        seen: Set[str] = set()
        out: List[str] = []
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out

    def list_missing_declared_packages(self) -> List[str]:
        """Declared packages that do not have a top-level node_modules folder."""
        return [p for p in self.get_declared_package_names() if not self.is_package_installed(p)]
        
    def is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed in node_modules"""
        package_path = os.path.join(self.nextjs_path, "node_modules", package_name)
        return os.path.exists(package_path)

    def install_all_from_package_json(self) -> bool:
        """Install every dependency and devDependency from package.json (single source of truth)."""
        npm_path = shutil.which("npm")
        if not npm_path:
            logging.error("npm not found in PATH")
            return False
        if not os.path.exists(self.package_json_path):
            logging.error("package.json not found: %s", self.package_json_path)
            return False

        env = os.environ.copy()
        env.setdefault("NPM_CONFIG_FUND", "false")
        env.setdefault("NPM_CONFIG_AUDIT", "false")

        def _run(cmd: List[str]) -> subprocess.CompletedProcess:
            return subprocess.run(
                cmd,
                cwd=self.nextjs_path,
                env=env,
                capture_output=True,
                text=True,
                check=True,
                timeout=3600,
            )

        try:
            if os.path.exists(self.package_lock_path):
                logging.info("Running npm ci in %s (reproducible install from lockfile)", self.nextjs_path)
                try:
                    _run(
                        [
                            npm_path,
                            "ci",
                            "--no-audit",
                            "--no-fund",
                            "--legacy-peer-deps",
                        ]
                    )
                except subprocess.CalledProcessError as e:
                    logging.warning(
                        "npm ci failed (%s), falling back to npm install",
                        (e.stderr or "")[-1500:],
                    )
                    _run(
                        [
                            npm_path,
                            "install",
                            "--no-progress",
                            "--prefer-offline",
                            "--no-audit",
                            "--no-fund",
                            "--legacy-peer-deps",
                        ]
                    )
            else:
                logging.info("No package-lock.json; running npm install in %s", self.nextjs_path)
                _run(
                    [
                        npm_path,
                        "install",
                        "--no-progress",
                        "--prefer-offline",
                        "--no-audit",
                        "--no-fund",
                        "--legacy-peer-deps",
                    ]
                )
            logging.info("Node dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(
                "npm install failed: %s",
                (e.stderr or e.stdout or "")[-4000:],
            )
            return False
        except subprocess.TimeoutExpired:
            logging.error("npm install timed out after 3600s")
            return False

    def ensure_node_dependencies(self) -> bool:
        """
        Ensure all packages listed in package.json are present under node_modules.
        If anything is missing, runs one full npm ci / npm install (not per-package).
        """
        if not os.path.exists(self.package_json_path):
            logging.error("package.json not found: %s", self.package_json_path)
            return False
        missing = self.list_missing_declared_packages()
        if not missing:
            logging.info("All declared Node dependencies are already installed")
            return True
        logging.info(
            "Installing Node dependencies (%d missing from node_modules, e.g. %s)",
            len(missing),
            ", ".join(missing[:12]) + ("..." if len(missing) > 12 else ""),
        )
        return self.install_all_from_package_json()
    
    def install_package(self, package_name: str, is_dev: bool = False) -> bool:
        """Install a single package (e.g. optional feature). Prefer ensure_node_dependencies for full UI setup."""
        npm_path = shutil.which('npm')
        if not npm_path:
            logging.error("npm not found in PATH")
            return False
            
        env = os.environ.copy()
        env.setdefault("NPM_CONFIG_FUND", "false")
        env.setdefault("NPM_CONFIG_AUDIT", "false")
        base = [npm_path, "install", "--no-progress", "--prefer-offline", "--no-audit", "--legacy-peer-deps"]
        if is_dev:
            base.append("--save-dev")
        base.append(package_name)
        try:
            subprocess.run(base, cwd=self.nextjs_path, env=env, capture_output=True, text=True, check=True, timeout=1800)
            logging.info("Installed %s", package_name)
            return True
        except subprocess.CalledProcessError as e:
            logging.error("Failed to install %s: %s", package_name, (e.stderr or "")[-2000:])
            return False
        
class DependencyCategories:
    # Mirrors dist/New_UI/package.json "dependencies" (for checks / docs; install uses package.json via DependencyManager)
    CORE_RUNTIME = [
        "@hookform/resolvers",
        "@radix-ui/react-alert-dialog",
        "@radix-ui/react-checkbox",
        "@radix-ui/react-dialog",
        "@radix-ui/react-dropdown-menu",
        "@radix-ui/react-label",
        "@radix-ui/react-popover",
        "@radix-ui/react-progress",
        "@radix-ui/react-scroll-area",
        "@radix-ui/react-select",
        "@radix-ui/react-slot",
        "@radix-ui/react-switch",
        "@radix-ui/react-tabs",
        "@radix-ui/react-toast",
        "@radix-ui/react-tooltip",
        "class-variance-authority",
        "clsx",
        "cmdk",
        "date-fns",
        "embla-carousel-react",
        "jszip",
        "lucide-react",
        "next-themes",
        "react",
        "react-day-picker",
        "react-dom",
        "react-hook-form",
        "react-resizable-panels",
        "recharts",
        "sonner",
        "tailwind-merge",
        "tailwindcss-animate",
        "vaul",
        "zod",
    ]
    
    # Mirrors dist/New_UI/package.json "devDependencies"
    BUILD_TOOLS = [
        "@tailwindcss/postcss",
        "@types/jszip",
        "@types/node",
        "@types/react",
        "@types/react-dom",
        "autoprefixer",
        "next",
        "postcss",
        "tailwindcss",
        "typescript",
    ]
    
    # Optional features (installed on demand via API; may overlap default package.json)
    OPTIONAL_FEATURES = {
        "charts": ["recharts"],
        "carousel": ["embla-carousel-react"],
        "otp": ["input-otp"],
        "drawer": ["vaul"],
        "command-palette": ["cmdk"],
    }


if __name__ == "__main__":
    # Used by start_tmxmatic.bat: install all UI packages from dist/New_UI/package.json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    _root = os.path.dirname(os.path.abspath(__file__))
    _dm = DependencyManager(_root)
    if not os.path.exists(_dm.package_json_path):
        logging.error("UI package.json not found: %s", _dm.package_json_path)
        raise SystemExit(1)
    if not _dm.ensure_node_dependencies():
        raise SystemExit(1)
    raise SystemExit(0)

