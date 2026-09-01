"""
Integration API handlers for Okapi services.

This module provides classes and functions to interact with Okapi APIs,
including authentication, file operations, and settings management.
"""

import os
import json
import logging
import requests
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

from ldw_core.okapi.github_policy import validate_github_repo

# Settings file paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
# Non-sensitive settings that are safe to commit (e.g. enabled flags)
SETTINGS_FILE = os.path.join(PROJECT_ROOT, 'integration_settings.json')
# Sensitive settings (API keys, URLs, project/workspace IDs) – should be gitignored
SECRETS_FILE = os.path.join(PROJECT_ROOT, 'integration_secrets.json')


class IntegrationSettings:
    """Manages integration settings storage and retrieval."""
    
    @staticmethod
    def _default_settings() -> Dict[str, Any]:
        """Base settings structure with defaults for all keys."""
        return {
            'okapi': {
                'enabled': False,
                'backend': 'docker',
                'docker_image': 'ldw-okapi-tikal:1.48',
                'tikal_path': '',
                'github_repo': '',
                'github_workflow': 'okapi-ops.yml',
                'github_branch': 'main',
                'github_token': '',
                'longhorn_url': '',
                'api_key': '',
                'api_url': '',
                'workspace_id': ''
            }
        }
    
    @staticmethod
    def load_settings() -> Dict[str, Any]:
        """
        Load integration settings from the public and secrets files.
        
        Public file:  integration_settings.json   (non-sensitive)
        Secrets file: integration_secrets.json    (API keys, URLs, IDs)
        """
        try:
            settings = IntegrationSettings._default_settings()

            # Load non-sensitive settings if present
            if os.path.exists(SETTINGS_FILE):
                try:
                    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        public_settings = json.load(f)
                        for key, value in public_settings.items():
                            if key in settings and isinstance(value, dict):
                                settings[key].update(value)
                except Exception as e:
                    logger.error(f"Error loading public settings: {e}")

            # Load sensitive settings if present (only merge sensitive keys so we don't overwrite 'enabled')
            _okapi_sensitive = {
                "api_key",
                "api_url",
                "workspace_id",
                "github_repo",
                "github_token",
            }
            if os.path.exists(SECRETS_FILE):
                try:
                    with open(SECRETS_FILE, 'r', encoding='utf-8') as f:
                        secret_settings = json.load(f)
                        for int_key, int_values in secret_settings.items():
                            if int_key not in settings or not isinstance(int_values, dict):
                                continue
                            for k, v in int_values.items():
                                if k in _okapi_sensitive:
                                    settings[int_key][k] = v
                except Exception as e:
                    logger.error(f"Error loading secret settings: {e}")

            return settings
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return IntegrationSettings._default_settings()
    
    @staticmethod
    def save_settings(settings: Dict[str, Any]) -> bool:
        """
        Save integration settings to two files:
        - integration_settings.json: non-sensitive values
        - integration_secrets.json: sensitive values (API keys, URLs, IDs)
        """
        try:
            # Ensure directory exists for both files (they share the same root)
            settings_dir = os.path.dirname(SETTINGS_FILE)
            if settings_dir and not os.path.exists(settings_dir):
                os.makedirs(settings_dir, exist_ok=True)

            # Define which keys are considered sensitive (only these go in secrets file)
            okapi_sensitive = {
                "api_key",
                "api_url",
                "workspace_id",
                "github_repo",
                "github_token",
            }

            public_settings = IntegrationSettings._default_settings()
            # Secrets file: only sensitive keys, so merging later won't overwrite 'enabled' etc.
            secret_settings = {'okapi': {}}

            okapi_in = settings.get('okapi', {})

            github_repo = okapi_in.get('github_repo', '')
            if github_repo:
                ok, err = validate_github_repo(github_repo)
                if not ok:
                    logger.error("Rejected github_repo: %s", err)
                    return False

            # Split Okapi settings
            for key, value in okapi_in.items():
                if key in okapi_sensitive:
                    secret_settings['okapi'][key] = value
                else:
                    public_settings['okapi'][key] = value

            # Write non-sensitive settings
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(public_settings, f, indent=2, ensure_ascii=False)

            # Write only sensitive keys so load merge doesn't overwrite enabled/ci_commands
            with open(SECRETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(secret_settings, f, indent=2, ensure_ascii=False)

            logger.info("Settings and secrets saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    @staticmethod
    def update_integration_settings(integration: str, settings: Dict[str, Any]) -> bool:
        """Update settings for a specific integration."""
        current_settings = IntegrationSettings.load_settings()
        if integration in current_settings:
            current_settings[integration].update(settings)
            return IntegrationSettings.save_settings(current_settings)
        return False


class OkapiAPI:
    """Client for interacting with Okapi Framework API."""
    
    def __init__(self, api_key: str, api_url: str, workspace_id: str):
        """
        Initialize Okapi API client.
        
        Args:
            api_key: Okapi API key
            api_url: Okapi API base URL.
                IMPORTANT:
                - This can be either the bare host (e.g. http://localhost:8000)
                  or a path with /api or /api/v1 (e.g. http://host/api/v1).
                - We normalize it so that requests are sent to the host root,
                  since the Okapi endpoints we use live under /workspaces/...,
                  not under /api or /api/v1.
            workspace_id: Okapi workspace ID
        """
        self.api_key = api_key
        base = api_url.rstrip('/')
        # If user includes /api or /api/v1 in the URL, strip it so that
        # all requests go to {host}/workspaces/... instead of {host}/api.../workspaces/...
        if base.endswith('/api/v1'):
            base = base[: -len('/api/v1')]
        elif base.endswith('/api'):
            base = base[: -len('/api')]
        self.api_url = base
        self.workspace_id = workspace_id
        self.session = requests.Session()
        # Okapi typically uses X-API-Key header or Authorization header
        self.session.headers.update({
            'X-API-Key': api_key,
            'Accept': 'application/json'
        })

    @staticmethod
    def _simplify_http_error(status_code: int, error_msg: str) -> str:
        """Return user-friendly messages for common HTTP failures."""
        msg = (error_msg or "").lower()
        if status_code in (401, 403):
            return "Authentication failed. Please verify your Okapi API key."
        if status_code == 404:
            if "workspace" in msg:
                return "Workspace not found. Please verify the Workspace ID."
            return "Okapi endpoint not found. Please verify the API URL."
        if status_code == 400:
            return "Request was rejected by Okapi. Please verify your settings."
        if status_code in (408, 504):
            return "Connection to Okapi timed out. Please try again."
        if status_code >= 500:
            return "Okapi server error. Please try again later."
        return "Could not connect to Okapi. Please verify your settings and try again."

    @staticmethod
    def _simplify_request_exception(exc: requests.exceptions.RequestException) -> str:
        """Normalize network-layer request errors into concise messages."""
        raw = str(exc)
        raw_lower = raw.lower()
        if isinstance(exc, requests.exceptions.ConnectTimeout) or "timed out" in raw_lower:
            return "Connection timed out. Please verify the API URL and server availability."
        if isinstance(exc, requests.exceptions.ConnectionError):
            if "name or service not known" in raw_lower or "nodename nor servname provided" in raw_lower:
                return "Cannot resolve Okapi host. Please check the API URL."
            if "failed to resolve" in raw_lower:
                return "Cannot resolve Okapi host. Please check the API URL."
            if "winerror 10061" in raw_lower or "actively refused" in raw_lower or "connection refused" in raw_lower:
                return "Cannot connect to Okapi server. Make sure it is running and the API URL is correct."
            return "Network connection to Okapi failed. Please verify the API URL."
        if isinstance(exc, requests.exceptions.SSLError):
            return "SSL error while connecting to Okapi. Please verify the HTTPS configuration."
        return "Connection test failed. Please verify settings and try again."
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Make an API request to Okapi.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base URL, e.g., '/workspaces/{id}')
            **kwargs: Additional arguments for requests
            
        Returns:
            Tuple of (success: bool, response_data: Optional[Dict])
        """
        try:
            # Remove leading slash and ensure proper endpoint format
            endpoint = endpoint.lstrip('/')
            url = f"{self.api_url}/{endpoint}"
            logger.info(f"Making {method} request to {url}")
            
            # Remove Content-Type from headers for file uploads (requests will set it)
            headers = kwargs.pop('headers', {})
            if 'files' not in kwargs:
                headers.setdefault('Content-Type', 'application/json')
            
            response = self.session.request(method, url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()
            
            # Handle empty responses
            if response.status_code == 204 or not response.content:
                return True, {'message': 'Success'}
            
            try:
                return True, response.json()
            except ValueError:
                return True, {'message': response.text, 'status_code': response.status_code}
                
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get('error', error_data.get('message', error_msg))
            except:
                error_msg = e.response.text or str(e)
            simplified = self._simplify_http_error(e.response.status_code, error_msg)
            logger.error(f"Okapi API HTTP error: {error_msg}")
            return False, {'error': simplified, 'status_code': e.response.status_code}
        except requests.exceptions.RequestException as e:
            logger.error(f"Okapi API request failed: {e}")
            return False, {'error': self._simplify_request_exception(e)}
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test the connection to Okapi API by verifying authentication and workspace access.
        
        Returns:
            Tuple of (success: bool, message: Optional[str])
        """
        # Try to verify authentication first
        success, data = self._make_request('GET', '/auth/verify')
        if not success:
            # Fallback: try to get workspace info
            success, data = self._make_request('GET', f'/workspaces/{self.workspace_id}')
        
        if success:
            return True, "Connection successful"
        error_msg = data.get('error', 'Connection failed') if data else 'Connection failed'
        return False, error_msg
    
    def upload_file(self, file_path: str, file_type: str = 'tmx', project_id: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Upload a translation file to Okapi workspace.
        
        Args:
            file_path: Path to the file to upload
            file_type: Type of file (tmx, xliff, xlf, etc.)
            project_id: Optional project ID within the workspace
            
        Returns:
            Tuple of (success: bool, response_data: Optional[Dict])
        """
        try:
            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f, self._get_content_type(file_type))
                }
                data = {
                    'workspace_id': self.workspace_id
                }
                if project_id:
                    data['project_id'] = project_id
                
                # Okapi typically uses: POST /api/v1/workspaces/{workspace_id}/files
                endpoint = f'/workspaces/{self.workspace_id}/upload-xlf'
                url = f"{self.api_url}/{endpoint.lstrip('/')}"
                
                # Remove Content-Type header for multipart/form-data
                headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
                
                logger.info(f"Uploading file to {url}")
                response = self.session.post(
                    url,
                    params={'api_key': self.api_key},   # <-- add this line
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=120,
                )
                response.raise_for_status()
                
                return True, response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get('error', error_data.get('message', error_msg))
            except:
                error_msg = e.response.text or str(e)
            logger.error(f"Error uploading file to Okapi: {error_msg}")
            return False, {'error': error_msg}
        except Exception as e:
            logger.error(f"Error uploading file to Okapi: {e}")
            return False, {'error': str(e)}
    
    def download_file(self, file_id: str, output_path: str) -> Tuple[bool, Optional[str]]:
        """
        Download a file from Okapi.
        
        Args:
            file_id: ID of the file to download
            output_path: Path where to save the file
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Okapi typically uses: GET /api/v1/files/{file_id}/download
            # or GET /api/v1/workspaces/{workspace_id}/files/{file_id}/download
            endpoint = f'/api/v1/workspaces/{self.workspace_id}/processed/{file_id}'
            print(self.api_url)
            url = f"{self.api_url}/{endpoint.lstrip('/')}"
            
            response = self.session.get(url, timeout=120, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True, None
        except Exception as e:
            logger.error(f"Error downloading file from Okapi: {e}")
            return False, str(e)
    
    def get_workspace_info(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Get information about the current workspace.
        
        Returns:
            Tuple of (success: bool, workspace_data: Optional[Dict])
        """
        return self._make_request('GET', f'/workspaces/{self.workspace_id}')
    
    def list_files(self, limit: int = 50, offset: int = 0, project_id: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        List files in the workspace.
        
        Args:
            limit: Maximum number of files to return
            offset: Number of files to skip
            project_id: Optional project ID to filter files
            
        Returns:
            Tuple of (success: bool, files_data: Optional[Dict])
        """
        params = {'limit': limit, 'offset': offset}
        if project_id:
            params['project_id'] = project_id
        
        # Primary endpoint: standard workspace files listing
        endpoint = f'/workspaces/{self.workspace_id}/files'
        success, result = self._make_request('GET', endpoint, params=params)
        if success:
            return True, result

        # If the server exposes processed XLFs under /workspaces/{workspace_id}/processed,
        # fall back to that endpoint specifically when the primary one returns 404.
        if isinstance(result, dict) and result.get('status_code') == 404:
            fallback_endpoint = f'/workspaces/{self.workspace_id}/processed'
            return self._make_request('GET', fallback_endpoint, params=params)

        # Otherwise, propagate the original error
        return False, result
    
    def list_projects(self, limit: int = 50, offset: int = 0) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        List projects in the workspace.
        
        Args:
            limit: Maximum number of projects to return
            offset: Number of projects to skip
            
        Returns:
            Tuple of (success: bool, projects_data: Optional[Dict])
        """
        params = {'limit': limit, 'offset': offset}
        endpoint = f'/workspaces/{self.workspace_id}/projects'
        return self._make_request('GET', endpoint, params=params)
    
    @staticmethod
    def _get_content_type(file_type: str) -> str:
        """Get MIME type for file type."""
        mime_types = {
            'tmx': 'application/x-tmx+xml',
            'xliff': 'application/xliff+xml',
            'xlf': 'application/xliff+xml',
            'xml': 'application/xml',
            'json': 'application/json'
        }
        return mime_types.get(file_type.lower(), 'application/octet-stream')


def get_okapi_client() -> Optional[OkapiAPI]:
    """Get a configured Okapi API client from settings."""
    settings = IntegrationSettings.load_settings()
    okapi = settings.get('okapi', {})
    
    if not okapi.get('enabled'):
        return None
    
    api_key = okapi.get('api_key', '')
    api_url = okapi.get('api_url', '')
    workspace_id = okapi.get('workspace_id', '')
    
    if not all([api_key, api_url, workspace_id]):
        logger.warning("Okapi settings incomplete")
        return None
    
    return OkapiAPI(api_key, api_url, workspace_id)


def test_integration_connection(
    integration: str,
    override_settings: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Test connection to a specific integration.
    
    Args:
        integration: 'okapi'
        override_settings: Optional dict with 'okapi' credentials
            to use for the test instead of saved settings (e.g. from current form).
        
    Returns:
        Tuple of (success: bool, message: Optional[str])
    """
    integration = integration.lower()
    overrides = (override_settings or {}).get(integration) or {}

    if integration == 'okapi':
        if overrides and all([overrides.get('api_key'), overrides.get('api_url'), overrides.get('workspace_id')]):
            client = OkapiAPI(
                overrides['api_key'],
                overrides['api_url'],
                overrides['workspace_id'],
            )
        else:
            client = get_okapi_client()
        if client:
            return client.test_connection()
        return False, "Okapi is not enabled or configured"

    return False, f"Unknown integration: {integration}"


def test_okapi_processing_backend(
    backend: str,
    okapi_settings: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Test Docker tikal or GitHub Actions Okapi backend using form or saved settings."""
    from ldw_core.okapi.config import load_okapi_config
    from ldw_core.okapi.runners import build_runner

    app_path = PROJECT_ROOT
    saved = IntegrationSettings.load_settings().get("okapi", {})
    cfg = {**saved, **(okapi_settings or {})}
    backend = (backend or cfg.get("backend") or "").strip().lower()
    if not backend:
        return False, "Select a processing backend first."

    if backend == "github":
        repo = (cfg.get("github_repo") or "").strip()
        ok, err = validate_github_repo(repo)
        if not ok:
            return False, err
        if not (cfg.get("github_token") or "").strip():
            return False, "Add a GitHub personal access token before testing."

    try:
        runner = build_runner(backend, app_path, cfg)
        health = runner.health_check()
        if health.available:
            return True, health.message
        return False, health.message
    except Exception as exc:
        logger.error("Okapi backend test failed: %s", exc)
        return False, str(exc)

