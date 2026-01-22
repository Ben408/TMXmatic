"""
Flask API Endpoints

REST API endpoints for translation and quality estimation.
"""
import logging
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
from typing import Dict, Optional
import tempfile
import os

from local_gpu_translation.integration.workflow_manager import WorkflowManager
from local_gpu_translation.llm_translation.translator import Translator
from shared.models.model_manager import ModelManager
from shared.models.memory_manager import MemoryManager
from shared.gpu.detector import GPUDetector
from shared.tqe.tqe import TQEEngine
from shared.config.profile_manager import ProfileManager
from shared.utils.logging import get_logger

logger = get_logger(__name__)

# Create Blueprint
local_gpu_bp = Blueprint('local_gpu', __name__)

# Global instances (initialized on first request)
_model_manager = None
_memory_manager = None
_translator = None
_tqe_engine = None
_gpu_detector = None


def get_model_manager() -> ModelManager:
    """Get or create ModelManager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def get_memory_manager() -> MemoryManager:
    """Get or create MemoryManager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def get_translator() -> Translator:
    """Get or create Translator instance."""
    global _translator
    if _translator is None:
        model_manager = get_model_manager()
        memory_manager = get_memory_manager()
        _translator = Translator(model_manager, memory_manager)
    return _translator


def get_tqe_engine() -> TQEEngine:
    """Get or create TQE engine instance."""
    global _tqe_engine
    if _tqe_engine is None:
        # Initialize with default settings
        _tqe_engine = TQEEngine(device="cuda")
    return _tqe_engine


def get_gpu_detector() -> GPUDetector:
    """Get or create GPU detector instance."""
    global _gpu_detector
    if _gpu_detector is None:
        _gpu_detector = GPUDetector()
    return _gpu_detector


@local_gpu_bp.route('/gpu/status', methods=['GET'])
def gpu_status():
    """Get GPU status and capabilities."""
    try:
        detector = get_gpu_detector()
        summary = detector.get_gpu_summary()
        return jsonify(summary), 200
    except Exception as e:
        logger.error(f"Error getting GPU status: {e}")
        return jsonify({'error': str(e)}), 500


@local_gpu_bp.route('/models/list', methods=['GET'])
def list_models():
    """List available models and their status."""
    try:
        model_manager = get_model_manager()
        models = model_manager.list_models()
        return jsonify({
            'models': [m.to_dict() for m in models]
        }), 200
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({'error': str(e)}), 500


@local_gpu_bp.route('/models/download', methods=['POST'])
def download_model():
    """Download a model."""
    try:
        data = request.get_json()
        model_id = data.get('model_id')
        
        if not model_id:
            return jsonify({'error': 'model_id required'}), 400
        
        model_manager = get_model_manager()
        model_path = model_manager.download_model(model_id)
        
        return jsonify({
            'model_id': model_id,
            'path': str(model_path),
            'status': 'downloaded'
        }), 200
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return jsonify({'error': str(e)}), 500


@local_gpu_bp.route('/translate', methods=['POST'])
def translate():
    """
    Translate XLIFF file.
    
    Request body:
    {
        "xliff_path": "path/to/file.xlf",
        "tmx_path": "path/to/file.tmx" (optional),
        "tbx_path": "path/to/file.tbx" (optional),
        "src_lang": "en",
        "tgt_lang": "fr",
        "profile_name": "default" (optional)
    }
    """
    try:
        data = request.get_json()
        xliff_path = Path(data.get('xliff_path'))
        tmx_path = Path(data.get('tmx_path')) if data.get('tmx_path') else None
        tbx_path = Path(data.get('tbx_path')) if data.get('tbx_path') else None
        src_lang = data.get('src_lang', 'en')
        tgt_lang = data.get('tgt_lang', 'fr')
        profile_name = data.get('profile_name')
        
        if not xliff_path.exists():
            return jsonify({'error': f'XLIFF file not found: {xliff_path}'}), 404
        
        # Get translator and TQE engine
        translator = get_translator()
        tqe_engine = get_tqe_engine()
        
        # Create workflow manager
        workflow_manager = WorkflowManager(translator, tqe_engine)
        
        # Setup workflow
        workflow_manager.setup_workflow(xliff_path, tmx_path, tbx_path, src_lang, tgt_lang)
        
        # Create output path
        output_path = xliff_path.parent / f"{xliff_path.stem}_translated.xlf"
        
        # Process XLIFF
        stats = workflow_manager.process_xliff(
            xliff_path, output_path, src_lang, tgt_lang
        )
        
        return jsonify({
            'status': 'success',
            'output_path': str(output_path),
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error in translation: {e}")
        return jsonify({'error': str(e)}), 500


@local_gpu_bp.route('/translate/download', methods=['GET'])
def download_translated():
    """Download translated XLIFF file."""
    try:
        output_path = request.args.get('path')
        if not output_path or not Path(output_path).exists():
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(output_path, as_attachment=True, download_name=Path(output_path).name)
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({'error': str(e)}), 500
