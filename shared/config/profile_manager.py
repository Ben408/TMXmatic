"""
Profile Management

Handles user-specific configuration profiles with global fallback.
"""
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Manages configuration profiles for users.
    
    Features:
    - User-specific profiles (when auth available)
    - Global profiles (fallback)
    - Profile CRUD operations
    - Global fallback for missing settings
    """
    
    def __init__(self, config_dir: Optional[Path] = None, user_id: Optional[str] = None):
        """
        Initialize ProfileManager.
        
        Args:
            config_dir: Base configuration directory. If None, uses default.
            user_id: Current user ID (if auth available). None for global-only mode.
        """
        if config_dir is None:
            # Default to project root / config
            project_root = Path(__file__).parent.parent.parent.parent
            config_dir = project_root / 'config'
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.profiles_dir = self.config_dir / 'profiles'
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        self.user_id = user_id
        self.user_profiles_dir = None
        self.global_profiles_dir = self.profiles_dir / 'global'
        self.global_profiles_dir.mkdir(parents=True, exist_ok=True)
        
        if user_id:
            self.user_profiles_dir = self.profiles_dir / user_id
            self.user_profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_profile_path(self, profile_name: str, user_specific: bool = True) -> Path:
        """
        Get path to profile file.
        
        Args:
            profile_name: Name of the profile
            user_specific: If True, use user-specific directory; if False, use global
        
        Returns:
            Path to profile file
        """
        if user_specific and self.user_profiles_dir:
            return self.user_profiles_dir / f"{profile_name}.json"
        else:
            return self.global_profiles_dir / f"{profile_name}.json"
    
    def create_profile(self, profile_name: str, settings: Dict[str, Any], 
                      user_specific: bool = True) -> bool:
        """
        Create a new profile.
        
        Args:
            profile_name: Name of the profile
            settings: Profile settings dictionary
            user_specific: If True, create user-specific profile; if False, create global
        
        Returns:
            True if created successfully, False otherwise
        """
        profile_path = self._get_profile_path(profile_name, user_specific)
        
        if profile_path.exists():
            logger.warning(f"Profile {profile_name} already exists")
            return False
        
        try:
            profile_data = {
                'name': profile_name,
                'created': datetime.now().isoformat(),
                'updated': datetime.now().isoformat(),
                'settings': settings
            }
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created profile: {profile_name} ({'user-specific' if user_specific else 'global'})")
            return True
            
        except Exception as e:
            logger.error(f"Error creating profile {profile_name}: {e}")
            return False
    
    def get_profile(self, profile_name: str, user_specific: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get a profile by name.
        
        Args:
            profile_name: Name of the profile
            user_specific: If True, look in user-specific directory first, then global
        
        Returns:
            Profile data dictionary, or None if not found
        """
        # Try user-specific first if requested
        if user_specific and self.user_profiles_dir:
            profile_path = self._get_profile_path(profile_name, user_specific=True)
            if profile_path.exists():
                try:
                    with open(profile_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error reading profile {profile_name}: {e}")
                    return None
        
        # Fall back to global
        profile_path = self._get_profile_path(profile_name, user_specific=False)
        if profile_path.exists():
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading profile {profile_name}: {e}")
                return None
        
        return None
    
    def update_profile(self, profile_name: str, settings: Dict[str, Any], 
                     user_specific: bool = True) -> bool:
        """
        Update an existing profile.
        
        Args:
            profile_name: Name of the profile
            settings: Updated settings dictionary
            user_specific: If True, update user-specific profile; if False, update global
        
        Returns:
            True if updated successfully, False otherwise
        """
        profile_path = self._get_profile_path(profile_name, user_specific)
        
        if not profile_path.exists():
            logger.warning(f"Profile {profile_name} does not exist")
            return False
        
        try:
            # Load existing profile
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
            
            # Update settings
            profile_data['settings'].update(settings)
            profile_data['updated'] = datetime.now().isoformat()
            
            # Save updated profile
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Updated profile: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating profile {profile_name}: {e}")
            return False
    
    def delete_profile(self, profile_name: str, user_specific: bool = True) -> bool:
        """
        Delete a profile.
        
        Args:
            profile_name: Name of the profile
            user_specific: If True, delete user-specific profile; if False, delete global
        
        Returns:
            True if deleted successfully, False otherwise
        """
        profile_path = self._get_profile_path(profile_name, user_specific)
        
        if not profile_path.exists():
            logger.warning(f"Profile {profile_name} does not exist")
            return False
        
        try:
            profile_path.unlink()
            logger.info(f"Deleted profile: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting profile {profile_name}: {e}")
            return False
    
    def list_profiles(self, include_global: bool = True) -> List[str]:
        """
        List available profiles.
        
        Args:
            include_global: If True, include global profiles in the list
        
        Returns:
            List of profile names
        """
        profiles = []
        
        # User-specific profiles
        if self.user_profiles_dir and self.user_profiles_dir.exists():
            for profile_file in self.user_profiles_dir.glob('*.json'):
                profiles.append(profile_file.stem)
        
        # Global profiles
        if include_global and self.global_profiles_dir.exists():
            for profile_file in self.global_profiles_dir.glob('*.json'):
                if profile_file.stem not in profiles:  # Avoid duplicates
                    profiles.append(profile_file.stem)
        
        return sorted(profiles)
    
    def get_setting(self, profile_name: Optional[str], setting_key: str, 
                   default: Any = None) -> Any:
        """
        Get a setting from a profile with global fallback.
        
        Args:
            profile_name: Name of the profile (None to use global defaults)
            setting_key: Key of the setting to retrieve
            default: Default value if setting not found
        
        Returns:
            Setting value, or default if not found
        """
        # Try user-specific profile first
        if profile_name:
            profile = self.get_profile(profile_name, user_specific=True)
            if profile and setting_key in profile.get('settings', {}):
                return profile['settings'][setting_key]
        
        # Try global profile
        if profile_name:
            profile = self.get_profile(profile_name, user_specific=False)
            if profile and setting_key in profile.get('settings', {}):
                return profile['settings'][setting_key]
        
        # Return default
        return default
    
    def get_active_profile_settings(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all settings from active profile with global fallback.
        
        Args:
            profile_name: Name of the active profile (None for global defaults)
        
        Returns:
            Dictionary of all settings
        """
        settings = {}
        
        # Load profile if specified
        if profile_name:
            profile = self.get_profile(profile_name, user_specific=True)
            if profile:
                settings.update(profile.get('settings', {}))
            else:
                # Try global
                profile = self.get_profile(profile_name, user_specific=False)
                if profile:
                    settings.update(profile.get('settings', {}))
        
        return settings
