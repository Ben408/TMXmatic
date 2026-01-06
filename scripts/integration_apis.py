"""
Integration API handlers for Blackbird and Okapi services.

This module provides classes and functions to interact with Blackbird and Okapi APIs,
including authentication, file operations, and settings management.
"""

import os
import json
import logging
import requests
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Settings file path
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'integration_settings.json')


class IntegrationSettings:
    """Manages integration settings storage and retrieval."""
    
    @staticmethod
    def load_settings() -> Dict[str, Any]:
        """Load integration settings from file."""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                'blackbird': {
                    'enabled': False,
                    'api_key': '',
                    'api_url': '',
                    'project_id': ''
                },
                'okapi': {
                    'enabled': False,
                    'api_key': '',
                    'api_url': '',
                    'workspace_id': ''
                }
            }
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return {
                'blackbird': {
                    'enabled': False,
                    'api_key': '',
                    'api_url': '',
                    'project_id': ''
                },
                'okapi': {
                    'enabled': False,
                    'api_key': '',
                    'api_url': '',
                    'workspace_id': ''
                }
            }
    
    @staticmethod
    def save_settings(settings: Dict[str, Any]) -> bool:
        """Save integration settings to file."""
        try:
            # Ensure directory exists
            settings_dir = os.path.dirname(SETTINGS_FILE)
            if settings_dir and not os.path.exists(settings_dir):
                os.makedirs(settings_dir, exist_ok=True)
            
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            logger.info("Settings saved successfully")
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


class BlackbirdAPI:
    """Client for interacting with Blackbird Translation Management System API."""
    
    def __init__(self, api_key: str, api_url: str, project_id: str):
        """
        Initialize Blackbird API client.
        
        Args:
            api_key: Blackbird API key/token
            api_url: Blackbird API base URL (e.g., https://api.blackbird.com or https://your-instance.blackbird.com/api/v1)
            project_id: Blackbird project ID
        """
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        # Ensure API URL has /api/v1 if not present
        if '/api/v1' not in self.api_url and '/api' not in self.api_url:
            self.api_url = f"{self.api_url}/api/v1"
        self.project_id = project_id
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Make an API request to Blackbird.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base URL, e.g., '/projects/{id}')
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
            logger.error(f"Blackbird API HTTP error: {error_msg}")
            return False, {'error': error_msg, 'status_code': e.response.status_code}
        except requests.exceptions.RequestException as e:
            logger.error(f"Blackbird API request failed: {e}")
            return False, {'error': str(e)}
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test the connection to Blackbird API by verifying authentication and project access.
        
        Returns:
            Tuple of (success: bool, message: Optional[str])
        """
        # Try to verify authentication first
        success, data = self._make_request('GET', '/auth/verify')
        if not success:
            # Fallback: try to get project info
            success, data = self._make_request('GET', f'/projects/{self.project_id}')
        
        if success:
            return True, "Connection successful"
        error_msg = data.get('error', 'Connection failed') if data else 'Connection failed'
        return False, error_msg
    
    def upload_file(self, file_path: str, file_type: str = 'tmx', target_language: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Upload a translation file to Blackbird project.
        
        Args:
            file_path: Path to the file to upload
            file_type: Type of file (tmx, xliff, xlf, etc.)
            target_language: Optional target language code (e.g., 'fr-CA', 'es-MX')
            
        Returns:
            Tuple of (success: bool, response_data: Optional[Dict])
        """
        try:
            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f, self._get_content_type(file_type))
                }
                data = {
                    'project_id': self.project_id
                }
                if target_language:
                    data['target_language'] = target_language
                
                # Blackbird typically uses: POST /api/v1/projects/{project_id}/files
                endpoint = f'/projects/{self.project_id}/files'
                url = f"{self.api_url}/{endpoint.lstrip('/')}"
                
                # Remove Content-Type header for multipart/form-data
                headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
                
                logger.info(f"Uploading file to {url}")
                response = self.session.post(url, files=files, data=data, headers=headers, timeout=120)
                response.raise_for_status()
                
                return True, response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get('error', error_data.get('message', error_msg))
            except:
                error_msg = e.response.text or str(e)
            logger.error(f"Error uploading file to Blackbird: {error_msg}")
            return False, {'error': error_msg}
        except Exception as e:
            logger.error(f"Error uploading file to Blackbird: {e}")
            return False, {'error': str(e)}
    
    def download_file(self, file_id: str, output_path: str) -> Tuple[bool, Optional[str]]:
        """
        Download a file from Blackbird.
        
        Args:
            file_id: ID of the file to download
            output_path: Path where to save the file
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Blackbird typically uses: GET /api/v1/files/{file_id}/download
            endpoint = f'/files/{file_id}/download'
            url = f"{self.api_url}/{endpoint.lstrip('/')}"
            
            response = self.session.get(url, timeout=120, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True, None
        except Exception as e:
            logger.error(f"Error downloading file from Blackbird: {e}")
            return False, str(e)
    
    def get_project_info(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Get information about the current project.
        
        Returns:
            Tuple of (success: bool, project_data: Optional[Dict])
        """
        return self._make_request('GET', f'/projects/{self.project_id}')
    
    def list_files(self, limit: int = 50, offset: int = 0) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        List files in the project.
        
        Args:
            limit: Maximum number of files to return
            offset: Number of files to skip
            
        Returns:
            Tuple of (success: bool, files_data: Optional[Dict])
        """
        params = {'limit': limit, 'offset': offset}
        return self._make_request('GET', f'/projects/{self.project_id}/files', params=params)
    
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


class OkapiAPI:
    """Client for interacting with Okapi Framework API."""
    
    def __init__(self, api_key: str, api_url: str, workspace_id: str):
        """
        Initialize Okapi API client.
        
        Args:
            api_key: Okapi API key
            api_url: Okapi API base URL (e.g., https://api.okapi.com or https://your-instance.okapi.com/api/v1)
            workspace_id: Okapi workspace ID
        """
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        # Ensure API URL has /api/v1 if not present
        if '/api/v1' not in self.api_url and '/api' not in self.api_url:
            self.api_url = f"{self.api_url}/api/v1"
        self.workspace_id = workspace_id
        self.session = requests.Session()
        # Okapi typically uses X-API-Key header or Authorization header
        self.session.headers.update({
            'X-API-Key': api_key,
            'Accept': 'application/json'
        })
    
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
            logger.error(f"Okapi API HTTP error: {error_msg}")
            return False, {'error': error_msg, 'status_code': e.response.status_code}
        except requests.exceptions.RequestException as e:
            logger.error(f"Okapi API request failed: {e}")
            return False, {'error': str(e)}
    
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
                endpoint = f'/workspaces/{self.workspace_id}/files'
                url = f"{self.api_url}/{endpoint.lstrip('/')}"
                
                # Remove Content-Type header for multipart/form-data
                headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
                
                logger.info(f"Uploading file to {url}")
                response = self.session.post(url, files=files, data=data, headers=headers, timeout=120)
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
            endpoint = f'/workspaces/{self.workspace_id}/files/{file_id}/download'
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
        
        endpoint = f'/workspaces/{self.workspace_id}/files'
        return self._make_request('GET', endpoint, params=params)
    
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


def get_blackbird_client() -> Optional[BlackbirdAPI]:
    """Get a configured Blackbird API client from settings."""
    settings = IntegrationSettings.load_settings()
    blackbird = settings.get('blackbird', {})
    
    if not blackbird.get('enabled'):
        return None
    
    api_key = blackbird.get('api_key', '')
    api_url = blackbird.get('api_url', '')
    project_id = blackbird.get('project_id', '')
    
    if not all([api_key, api_url, project_id]):
        logger.warning("Blackbird settings incomplete")
        return None
    
    return BlackbirdAPI(api_key, api_url, project_id)


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


def test_integration_connection(integration: str) -> Tuple[bool, Optional[str]]:
    """
    Test connection to a specific integration.
    
    Args:
        integration: 'blackbird' or 'okapi'
        
    Returns:
        Tuple of (success: bool, message: Optional[str])
    """
    if integration.lower() == 'blackbird':
        client = get_blackbird_client()
        if client:
            return client.test_connection()
        return False, "Blackbird is not enabled or configured"
    
    elif integration.lower() == 'okapi':
        client = get_okapi_client()
        if client:
            return client.test_connection()
        return False, "Okapi is not enabled or configured"
    
    return False, f"Unknown integration: {integration}"

