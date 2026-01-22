"""
Pytest configuration and shared fixtures for LLM Quality Module tests.
"""
import pytest
import sys
from pathlib import Path
import tempfile
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def project_root_path():
    """Return the project root directory as a Path object."""
    return Path(__file__).parent.parent

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def fixtures_dir(project_root_path):
    """Return the fixtures directory path."""
    return project_root_path / "tests" / "fixtures"

@pytest.fixture
def sample_xliff_path():
    """Return path to sample XLIFF file."""
    # Use actual test file provided by user
    return Path(r"C:\Users\bjcor\Desktop\Sage Local\SW XLIFF\error message.xlf")

@pytest.fixture
def sample_tmx_path():
    """Return path to sample TMX file."""
    # Use actual test file from Test_files directory
    return Path(r"C:\Users\bjcor\Desktop\TMXmatic\Test_files\Trados EN-FR.tmx")

@pytest.fixture
def sample_tbx_path():
    """Return path to sample TBX file."""
    # Use actual test file provided by user
    return Path(r"C:\Users\bjcor\Desktop\Sage Local\SDMO Glossary\SDMO_multilingual_merged.tbx")

@pytest.fixture
def tmx_test_files_dir():
    """Return directory containing TMX test files."""
    return Path(r"C:\Users\bjcor\Desktop\TMXmatic\Test_files")

@pytest.fixture
def mock_gpu_available(monkeypatch):
    """Mock GPU as available."""
    def mock_cuda_available():
        return True
    
    def mock_cuda_device_count():
        return 1
    
    def mock_get_device_properties(device_id):
        class MockDevice:
            total_memory = 12 * 1024 * 1024 * 1024  # 12GB
            name = "Mock RTX GPU"
        return MockDevice()
    
    try:
        import torch
        monkeypatch.setattr(torch.cuda, "is_available", mock_cuda_available)
        monkeypatch.setattr(torch.cuda, "device_count", mock_cuda_device_count)
        monkeypatch.setattr(torch.cuda, "get_device_properties", mock_get_device_properties)
    except ImportError:
        pass

@pytest.fixture
def mock_gpu_unavailable(monkeypatch):
    """Mock GPU as unavailable."""
    def mock_cuda_available():
        return False
    
    try:
        import torch
        monkeypatch.setattr(torch.cuda, "is_available", mock_cuda_available)
    except ImportError:
        pass

@pytest.fixture
def mock_model_download(monkeypatch):
    """Mock model downloads to avoid downloading large files in tests."""
    def mock_download(*args, **kwargs):
        # Return a mock path
        return Path(tempfile.mkdtemp())
    
    try:
        from huggingface_hub import snapshot_download
        monkeypatch.setattr("huggingface_hub.snapshot_download", mock_download)
    except ImportError:
        pass
