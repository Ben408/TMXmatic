"""
Unit tests for Flask API endpoints.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.api.endpoints import (
    local_gpu_bp, get_model_manager, get_memory_manager,
    get_translator, get_tqe_engine, get_gpu_detector
)


class TestAPIEndpoints:
    """Tests for API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create Flask app for testing."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(local_gpu_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @patch('local_gpu_translation.api.endpoints.GPUDetector')
    def test_gpu_status(self, mock_detector_class, client):
        """Test GPU status endpoint."""
        mock_detector = Mock()
        mock_detector.get_gpu_summary.return_value = {
            'cuda_available': True,
            'gpu_count': 1,
            'gpus': [{'name': 'RTX 4090', 'memory_gb': 24}]
        }
        mock_detector_class.return_value = mock_detector
        
        response = client.get('/gpu/status')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'cuda_available' in data
    
    @patch('local_gpu_translation.api.endpoints.ModelManager')
    def test_list_models(self, mock_model_manager_class, client):
        """Test list models endpoint."""
        mock_manager = Mock()
        mock_model = Mock()
        mock_model.to_dict.return_value = {'id': 'test-model', 'name': 'Test Model'}
        mock_manager.list_models.return_value = [mock_model]
        mock_model_manager_class.return_value = mock_manager
        
        response = client.get('/models/list')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'models' in data
        assert len(data['models']) > 0
    
    @patch('local_gpu_translation.api.endpoints.ModelManager')
    def test_download_model(self, mock_model_manager_class, client):
        """Test download model endpoint."""
        mock_manager = Mock()
        mock_manager.download_model.return_value = Path('/path/to/model')
        mock_model_manager_class.return_value = mock_manager
        
        response = client.post('/models/download', json={'model_id': 'test-model'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'downloaded'
        assert 'path' in data
    
    def test_download_model_missing_id(self, client):
        """Test download model without model_id."""
        response = client.post('/models/download', json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    @patch('local_gpu_translation.api.endpoints.WorkflowManager')
    @patch('local_gpu_translation.api.endpoints.get_translator')
    @patch('local_gpu_translation.api.endpoints.get_tqe_engine')
    def test_translate_endpoint(self, mock_get_tqe, mock_get_translator, 
                               mock_workflow_class, client, temp_dir):
        """Test translate endpoint."""
        # Create test XLIFF file
        xliff_path = temp_dir / "test.xlf"
        xliff_path.write_text('<?xml version="1.0"?><xliff version="2.0"><file><unit id="1"><source>Hello</source></unit></file></xliff>')
        
        # Mock workflow manager
        mock_workflow = Mock()
        mock_workflow.setup_workflow.return_value = True
        mock_workflow.process_xliff.return_value = {
            'total': 1, 'processed': 1, 'exact_matches': 0,
            'fuzzy_repairs': 0, 'new_translations': 1, 'errors': 0
        }
        mock_workflow_class.return_value = mock_workflow
        
        # Mock translator and TQE
        mock_translator = Mock()
        mock_tqe = Mock()
        mock_get_translator.return_value = mock_translator
        mock_get_tqe.return_value = mock_tqe
        
        response = client.post('/translate', json={
            'xliff_path': str(xliff_path),
            'src_lang': 'en',
            'tgt_lang': 'fr'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'statistics' in data
    
    def test_translate_missing_file(self, client):
        """Test translate with missing XLIFF file."""
        response = client.post('/translate', json={
            'xliff_path': '/nonexistent/file.xlf',
            'src_lang': 'en',
            'tgt_lang': 'fr'
        })
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
