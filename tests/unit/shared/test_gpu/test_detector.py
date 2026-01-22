"""
Unit tests for GPU detector.

Tests GPU detection, information retrieval, and requirement checking.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.gpu.detector import GPUDetector, GPUInfo


class TestGPUInfo:
    """Tests for GPUInfo class."""
    
    def test_gpu_info_creation(self):
        """Test GPUInfo object creation."""
        gpu_info = GPUInfo(
            device_id=0,
            name="Test GPU",
            total_memory_gb=12.0,
            available_memory_gb=10.0
        )
        
        assert gpu_info.device_id == 0
        assert gpu_info.name == "Test GPU"
        assert gpu_info.total_memory_gb == 12.0
        assert gpu_info.available_memory_gb == 10.0
    
    def test_gpu_info_to_dict(self):
        """Test GPUInfo to_dict conversion."""
        gpu_info = GPUInfo(
            device_id=0,
            name="Test GPU",
            total_memory_gb=12.0,
            available_memory_gb=10.0
        )
        
        result = gpu_info.to_dict()
        
        assert result['device_id'] == 0
        assert result['name'] == "Test GPU"
        assert result['total_memory_gb'] == 12.0
        assert result['available_memory_gb'] == 10.0
    
    def test_gpu_info_repr(self):
        """Test GPUInfo string representation."""
        gpu_info = GPUInfo(
            device_id=0,
            name="Test GPU",
            total_memory_gb=12.0,
            available_memory_gb=10.0
        )
        
        repr_str = repr(gpu_info)
        assert "GPUInfo" in repr_str
        assert "Test GPU" in repr_str
        assert "12.0" in repr_str


class TestGPUDetector:
    """Tests for GPUDetector class."""
    
    def test_detector_initialization(self):
        """Test GPUDetector initialization."""
        detector = GPUDetector()
        assert detector._cuda_available is None
        assert detector._gpu_info is None
    
    @patch('torch.cuda.is_available')
    def test_cuda_available_true(self, mock_is_available):
        """Test CUDA availability check when CUDA is available."""
        mock_is_available.return_value = True
        
        detector = GPUDetector()
        result = detector.is_cuda_available()
        
        assert result is True
        assert detector._cuda_available is True
    
    @patch('torch.cuda.is_available')
    def test_cuda_available_false(self, mock_is_available):
        """Test CUDA availability check when CUDA is not available."""
        mock_is_available.return_value = False
        
        detector = GPUDetector()
        result = detector.is_cuda_available()
        
        assert result is False
        assert detector._cuda_available is False
    
    def test_cuda_available_no_torch(self):
        """Test CUDA availability check when PyTorch is not installed."""
        # Temporarily remove torch from sys.modules if present
        torch_backup = sys.modules.pop('torch', None)
        try:
            detector = GPUDetector()
            result = detector.is_cuda_available()
            
            assert result is False
            assert detector._cuda_available is False
        finally:
            if torch_backup:
                sys.modules['torch'] = torch_backup
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    def test_get_gpu_count(self, mock_device_count, mock_is_available):
        """Test getting GPU count."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 2
        
        detector = GPUDetector()
        count = detector.get_gpu_count()
        
        assert count == 2
    
    @patch('torch.cuda.is_available')
    def test_get_gpu_count_no_cuda(self, mock_is_available):
        """Test getting GPU count when CUDA is not available."""
        mock_is_available.return_value = False
        
        detector = GPUDetector()
        count = detector.get_gpu_count()
        
        assert count == 0
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_get_gpu_info(self, mock_memory_reserved, mock_memory_allocated, 
                          mock_set_device, mock_get_props, mock_device_count, mock_is_available):
        """Test getting GPU information."""
        # Setup mocks
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.name = "RTX 3080"
        mock_props.total_memory = 12 * 1024 * 1024 * 1024  # 12GB
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 0
        mock_memory_reserved.return_value = 0
        
        detector = GPUDetector()
        gpu_info = detector.get_gpu_info(0)
        
        assert gpu_info is not None
        assert gpu_info.device_id == 0
        assert gpu_info.name == "RTX 3080"
        assert gpu_info.total_memory_gb == pytest.approx(12.0, rel=0.1)
    
    @patch('torch.cuda.is_available')
    def test_get_gpu_info_no_cuda(self, mock_is_available):
        """Test getting GPU info when CUDA is not available."""
        mock_is_available.return_value = False
        
        detector = GPUDetector()
        gpu_info = detector.get_gpu_info(0)
        
        assert gpu_info is None
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_get_all_gpus(self, mock_memory_reserved, mock_memory_allocated,
                          mock_set_device, mock_get_props, mock_device_count, mock_is_available):
        """Test getting all GPUs."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 2
        
        mock_props = Mock()
        mock_props.name = "RTX 3080"
        mock_props.total_memory = 12 * 1024 * 1024 * 1024
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 0
        mock_memory_reserved.return_value = 0
        
        detector = GPUDetector()
        gpus = detector.get_all_gpus()
        
        assert len(gpus) == 2
        assert all(isinstance(gpu, GPUInfo) for gpu in gpus)
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_check_gpu_requirements_meets(self, mock_memory_reserved, mock_memory_allocated,
                                          mock_set_device, mock_get_props, mock_device_count, mock_is_available):
        """Test GPU requirements check when requirements are met."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.name = "RTX 3080"
        mock_props.total_memory = 12 * 1024 * 1024 * 1024
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 0
        mock_memory_reserved.return_value = 0
        
        detector = GPUDetector()
        meets, error = detector.check_gpu_requirements(min_memory_gb=8.0)
        
        assert meets is True
        assert error is None
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_check_gpu_requirements_insufficient_memory(self, mock_memory_reserved, mock_memory_allocated,
                                                          mock_set_device, mock_get_props, mock_device_count, mock_is_available):
        """Test GPU requirements check when memory is insufficient."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.name = "RTX 3060"
        mock_props.total_memory = 6 * 1024 * 1024 * 1024  # 6GB
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 0
        mock_memory_reserved.return_value = 0
        
        detector = GPUDetector()
        meets, error = detector.check_gpu_requirements(min_memory_gb=8.0)
        
        assert meets is False
        assert error is not None
        assert "minimum requirement" in error.lower()
    
    @patch('torch.cuda.is_available')
    def test_check_gpu_requirements_no_cuda(self, mock_is_available):
        """Test GPU requirements check when CUDA is not available."""
        mock_is_available.return_value = False
        
        detector = GPUDetector()
        meets, error = detector.check_gpu_requirements(min_memory_gb=8.0)
        
        assert meets is False
        assert error is not None
        assert "CUDA is not available" in error
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.device_count')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.set_device')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_get_gpu_summary(self, mock_memory_reserved, mock_memory_allocated,
                             mock_set_device, mock_get_props, mock_device_count, mock_is_available):
        """Test getting GPU summary."""
        mock_is_available.return_value = True
        mock_device_count.return_value = 1
        
        mock_props = Mock()
        mock_props.name = "RTX 3080"
        mock_props.total_memory = 12 * 1024 * 1024 * 1024
        
        mock_get_props.return_value = mock_props
        mock_memory_allocated.return_value = 0
        mock_memory_reserved.return_value = 0
        
        detector = GPUDetector()
        summary = detector.get_gpu_summary()
        
        assert summary['cuda_available'] is True
        assert summary['gpu_count'] == 1
        assert len(summary['gpus']) == 1
        assert summary['gpus'][0]['name'] == "RTX 3080"


class TestDetectGPUFunction:
    """Tests for detect_gpu convenience function."""
    
    def test_detect_gpu_function(self):
        """Test detect_gpu convenience function."""
        from shared.gpu.detector import detect_gpu
        
        detector = detect_gpu()
        
        assert isinstance(detector, GPUDetector)
