"""
Unit tests for profile manager.

Tests profile CRUD operations, user-specific profiles, and global fallback.
"""
import pytest
import json
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.config.profile_manager import ProfileManager


class TestProfileManager:
    """Tests for ProfileManager class."""
    
    def test_profile_manager_initialization_default(self, temp_dir):
        """Test ProfileManager initialization with default directory."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        assert manager.config_dir.exists()
        assert manager.profiles_dir.exists()
        assert manager.global_profiles_dir.exists()
    
    def test_profile_manager_initialization_with_user(self, temp_dir):
        """Test ProfileManager initialization with user ID."""
        manager = ProfileManager(config_dir=temp_dir / 'config', user_id='user123')
        
        assert manager.user_id == 'user123'
        assert manager.user_profiles_dir.exists()
        assert manager.global_profiles_dir.exists()
    
    def test_create_profile_user_specific(self, temp_dir):
        """Test creating a user-specific profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config', user_id='user123')
        
        settings = {
            'fuzzy_threshold': 0.75,
            'batch_size': 10
        }
        
        result = manager.create_profile('test-profile', settings, user_specific=True)
        
        assert result is True
        profile_path = manager.user_profiles_dir / 'test-profile.json'
        assert profile_path.exists()
    
    def test_create_profile_global(self, temp_dir):
        """Test creating a global profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        settings = {
            'fuzzy_threshold': 0.8,
            'batch_size': 5
        }
        
        result = manager.create_profile('global-profile', settings, user_specific=False)
        
        assert result is True
        profile_path = manager.global_profiles_dir / 'global-profile.json'
        assert profile_path.exists()
    
    def test_create_profile_duplicate(self, temp_dir):
        """Test creating a duplicate profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        settings = {'test': 'value'}
        manager.create_profile('test-profile', settings)
        
        # Try to create again
        result = manager.create_profile('test-profile', settings)
        
        assert result is False
    
    def test_get_profile_user_specific(self, temp_dir):
        """Test getting a user-specific profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config', user_id='user123')
        
        settings = {'fuzzy_threshold': 0.75}
        manager.create_profile('test-profile', settings, user_specific=True)
        
        profile = manager.get_profile('test-profile', user_specific=True)
        
        assert profile is not None
        assert profile['name'] == 'test-profile'
        assert profile['settings']['fuzzy_threshold'] == 0.75
    
    def test_get_profile_global_fallback(self, temp_dir):
        """Test getting a profile with global fallback."""
        manager = ProfileManager(config_dir=temp_dir / 'config', user_id='user123')
        
        # Create global profile only
        settings = {'fuzzy_threshold': 0.8}
        manager.create_profile('test-profile', settings, user_specific=False)
        
        # Get profile (should fall back to global)
        profile = manager.get_profile('test-profile', user_specific=True)
        
        assert profile is not None
        assert profile['settings']['fuzzy_threshold'] == 0.8
    
    def test_get_profile_not_found(self, temp_dir):
        """Test getting a non-existent profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        profile = manager.get_profile('nonexistent')
        
        assert profile is None
    
    def test_update_profile(self, temp_dir):
        """Test updating a profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        settings = {'fuzzy_threshold': 0.75}
        manager.create_profile('test-profile', settings)
        
        # Update profile
        new_settings = {'batch_size': 20}
        result = manager.update_profile('test-profile', new_settings)
        
        assert result is True
        
        # Verify update
        profile = manager.get_profile('test-profile')
        assert profile['settings']['fuzzy_threshold'] == 0.75  # Original preserved
        assert profile['settings']['batch_size'] == 20  # New setting added
    
    def test_update_profile_not_found(self, temp_dir):
        """Test updating a non-existent profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        result = manager.update_profile('nonexistent', {'test': 'value'})
        
        assert result is False
    
    def test_delete_profile(self, temp_dir):
        """Test deleting a profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        settings = {'test': 'value'}
        manager.create_profile('test-profile', settings)
        
        result = manager.delete_profile('test-profile')
        
        assert result is True
        profile = manager.get_profile('test-profile')
        assert profile is None
    
    def test_delete_profile_not_found(self, temp_dir):
        """Test deleting a non-existent profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        result = manager.delete_profile('nonexistent')
        
        assert result is False
    
    def test_list_profiles(self, temp_dir):
        """Test listing profiles."""
        manager = ProfileManager(config_dir=temp_dir / 'config', user_id='user123')
        
        # Create user-specific profile
        manager.create_profile('user-profile', {'test': 'value'}, user_specific=True)
        
        # Create global profile
        manager.create_profile('global-profile', {'test': 'value'}, user_specific=False)
        
        profiles = manager.list_profiles(include_global=True)
        
        assert 'user-profile' in profiles
        assert 'global-profile' in profiles
    
    def test_get_setting(self, temp_dir):
        """Test getting a setting from a profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        settings = {'fuzzy_threshold': 0.75, 'batch_size': 10}
        manager.create_profile('test-profile', settings)
        
        # Get setting
        value = manager.get_setting('test-profile', 'fuzzy_threshold', default=0.8)
        
        assert value == 0.75
    
    def test_get_setting_not_found(self, temp_dir):
        """Test getting a setting that doesn't exist."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        settings = {'fuzzy_threshold': 0.75}
        manager.create_profile('test-profile', settings)
        
        # Get non-existent setting
        value = manager.get_setting('test-profile', 'nonexistent', default='default')
        
        assert value == 'default'
    
    def test_get_active_profile_settings(self, temp_dir):
        """Test getting all settings from active profile."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        settings = {'fuzzy_threshold': 0.75, 'batch_size': 10}
        manager.create_profile('test-profile', settings)
        
        all_settings = manager.get_active_profile_settings('test-profile')
        
        assert all_settings['fuzzy_threshold'] == 0.75
        assert all_settings['batch_size'] == 10
    
    def test_get_active_profile_settings_no_profile(self, temp_dir):
        """Test getting settings when no profile is active."""
        manager = ProfileManager(config_dir=temp_dir / 'config')
        
        settings = manager.get_active_profile_settings()
        
        assert isinstance(settings, dict)
        assert len(settings) == 0
