"""
Unit tests for memory manager.

Tests GPU memory monitoring, batch size calculation, and OOM risk checking.
"""
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.models.memory_manager import MemoryManager, MemoryStats


class TestMemoryStats:
    """Tests for MemoryStats dataclass."""
    
    def test_memory_stats_creation(self):
        """Test MemoryStats object creation."""
        stats = MemoryStats(
            total_memory_gb=12.0,
            allocated_memory_gb=4.0,
            reserved_memory_gb=5.0,
            free_memory_gb=7.0,
            utilization_percent=41.67
        )
        
        assert stats.total_memory_gb == 12.0
        assert stats.allocated_memory_gb == 4.0
        assert stats.reserved_memory_gb == 5.0
        assert stats.free_memory_gb == 7.0
        assert stats.utilization_percent == pytest.approx(41.67, rel=0.1)


class TestMemoryManager:
    """Tests for MemoryManager class."""
    
    def test_memory_manager_initialization(self):
        """Test MemoryManager initialization."""
        manager = MemoryManager(device_id=0, safety_margin_gb=1.0)
        
        assert manager.device_id == 0
        assert manager.safety_margin_gb == 1.0
        assert len(manager._loaded_models) == 0
    
    def test_memory_manager_initialization_custom(self):
        """Test MemoryManager initialization with custom parameters."""
        manager = MemoryManager(device_id=1, safety_margin_gb=2.0)
        
        assert manager.device_id == 1
        assert manager.safety_margin_gb == 2.0
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_get_memory_stats(self, mock_memory_reserved, mock_memory_allocated,
                              mock_get_props, mock_set_device, mock_device_count, mock_is_available):
        """Test getting memory statistics."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.total_memory = 12 * 1024 * 1024 * 1024  # 12GB
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory_reserved.return_value = 5 * 1024 * 1024 * 1024  # 5GB
        
        manager = MemoryManager()
        stats = manager.get_memory_stats()
        
        assert stats is not None
        assert stats.total_memory_gb == pytest.approx(12.0, rel=0.1)
        assert stats.allocated_memory_gb == pytest.approx(4.0, rel=0.1)
        assert stats.reserved_memory_gb == pytest.approx(5.0, rel=0.1)
        assert stats.free_memory_gb == pytest.approx(7.0, rel=0.1)
    
    @patch('torch.cuda.is_available')
    def test_get_memory_stats_no_cuda(self, mock_is_available):
        """Test getting memory stats when CUDA is not available."""
        mock_is_available.return_value = False
        
        manager = MemoryManager()
        stats = manager.get_memory_stats()
        
        assert stats is None
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_get_available_memory_gb(self, mock_memory_reserved, mock_memory_allocated,
                                     mock_get_props, mock_set_device, mock_device_count, mock_is_available):
        """Test getting available memory."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.total_memory = 12 * 1024 * 1024 * 1024  # 12GB
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory_reserved.return_value = 5 * 1024 * 1024 * 1024  # 5GB
        
        manager = MemoryManager(safety_margin_gb=1.0)
        available = manager.get_available_memory_gb()
        
        # 12GB total - 5GB reserved - 1GB safety margin = 6GB available
        assert available == pytest.approx(6.0, rel=0.1)
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_can_load_model(self, mock_memory_reserved, mock_memory_allocated,
                           mock_get_props, mock_set_device, mock_device_count, mock_is_available):
        """Test checking if model can be loaded."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.total_memory = 12 * 1024 * 1024 * 1024  # 12GB
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory_reserved.return_value = 5 * 1024 * 1024 * 1024  # 5GB
        
        manager = MemoryManager(safety_margin_gb=1.0)
        
        # Can load 5GB model (6GB available)
        assert manager.can_load_model(5.0) is True
        
        # Cannot load 7GB model (only 6GB available)
        assert manager.can_load_model(7.0) is False
    
    def test_register_loaded_model(self):
        """Test registering a loaded model."""
        manager = MemoryManager()
        mock_model = Mock()
        
        manager.register_loaded_model('test-model', mock_model, 2.0)
        
        assert 'test-model' in manager._loaded_models
        assert manager._loaded_models['test-model']['model'] == mock_model
        assert manager._loaded_models['test-model']['estimated_size_gb'] == 2.0
    
    def test_unregister_model(self):
        """Test unregistering a model."""
        manager = MemoryManager()
        mock_model = Mock()
        
        manager.register_loaded_model('test-model', mock_model, 2.0)
        assert 'test-model' in manager._loaded_models
        
        manager.unregister_model('test-model')
        assert 'test-model' not in manager._loaded_models
    
    def test_get_loaded_models(self):
        """Test getting list of loaded models."""
        manager = MemoryManager()
        mock_model1 = Mock()
        mock_model2 = Mock()
        
        manager.register_loaded_model('model1', mock_model1, 2.0)
        manager.register_loaded_model('model2', mock_model2, 3.0)
        
        loaded = manager.get_loaded_models()
        
        assert len(loaded) == 2
        assert 'model1' in loaded
        assert 'model2' in loaded
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_calculate_optimal_batch_size(self, mock_memory_reserved, mock_memory_allocated,
                                         mock_get_props, mock_set_device, mock_device_count, mock_is_available):
        """Test calculating optimal batch size."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.total_memory = 12 * 1024 * 1024 * 1024  # 12GB
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory_reserved.return_value = 5 * 1024 * 1024 * 1024  # 5GB
        
        manager = MemoryManager(safety_margin_gb=1.0)
        
        # With 6GB available and 100MB per item, should be able to fit many items
        batch_size = manager.calculate_optimal_batch_size(base_batch_size=1, memory_per_item_mb=100.0)
        
        assert batch_size >= 1
        assert batch_size <= 100  # Reasonable upper bound
    
    @patch('torch.cuda.is_available')
    def test_calculate_optimal_batch_size_no_gpu(self, mock_is_available):
        """Test calculating batch size when GPU is unavailable."""
        mock_is_available.return_value = False
        
        manager = MemoryManager()
        batch_size = manager.calculate_optimal_batch_size(base_batch_size=4)
        
        # Should return base batch size when GPU unavailable
        assert batch_size == 4
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_check_oom_risk_safe(self, mock_memory_reserved, mock_memory_allocated,
                                 mock_get_props, mock_set_device, mock_device_count, mock_is_available):
        """Test OOM risk check when safe."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.total_memory = 12 * 1024 * 1024 * 1024  # 12GB
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory_reserved.return_value = 5 * 1024 * 1024 * 1024  # 5GB
        
        manager = MemoryManager(safety_margin_gb=1.0)
        is_safe, warning = manager.check_oom_risk(additional_memory_gb=2.0)
        
        assert is_safe is True
        assert warning is None
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_check_oom_risk_insufficient(self, mock_memory_reserved, mock_memory_allocated,
                                         mock_get_props, mock_set_device, mock_device_count, mock_is_available):
        """Test OOM risk check when insufficient memory."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.total_memory = 12 * 1024 * 1024 * 1024  # 12GB
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory_reserved.return_value = 5 * 1024 * 1024 * 1024  # 5GB
        
        manager = MemoryManager(safety_margin_gb=1.0)
        is_safe, warning = manager.check_oom_risk(additional_memory_gb=10.0)
        
        assert is_safe is False
        assert warning is not None
        assert "Insufficient memory" in warning
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_get_memory_summary(self, mock_memory_reserved, mock_memory_allocated,
                               mock_get_props, mock_set_device, mock_device_count, mock_is_available):
        """Test getting memory summary."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.total_memory = 12 * 1024 * 1024 * 1024  # 12GB
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory_reserved.return_value = 5 * 1024 * 1024 * 1024  # 5GB
        
        manager = MemoryManager()
        manager.register_loaded_model('test-model', Mock(), 2.0)
        
        summary = manager.get_memory_summary()
        
        assert summary['available'] is True
        assert summary['device_id'] == 0
        assert 'total_memory_gb' in summary
        assert 'loaded_models' in summary
        assert 'test-model' in summary['loaded_models']
        assert summary['loaded_model_count'] == 1
