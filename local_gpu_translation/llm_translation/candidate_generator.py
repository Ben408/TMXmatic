"""
Candidate Generator

Generates N-best translation candidates using local LLM.
"""
import logging
from typing import List, Optional, Dict
import torch

from shared.models.model_manager import ModelManager
from shared.models.memory_manager import MemoryManager
from shared.utils.error_recovery import retry_on_error

logger = logging.getLogger(__name__)

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
    from threading import Thread
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available")


class CandidateGenerator:
    """
    Generates translation candidates using local LLM.
    
    Features:
    - Load translategemma-12b-it model
    - Generate N-best candidates
    - Support term injection via prompts
    - Keep model loaded for performance
    """
    
    def __init__(self, model_manager: ModelManager, memory_manager: MemoryManager,
                 device: str = "cuda", model_id: str = "translategemma-12b-it",
                 num_candidates: int = 5):
        """
        Initialize CandidateGenerator.
        
        Args:
            model_manager: ModelManager instance
            memory_manager: MemoryManager instance
            device: Device to use ('cuda' or 'cpu')
            model_id: Model identifier
            num_candidates: Number of candidates to generate
        """
        self.model_manager = model_manager
        self.memory_manager = memory_manager
        self.device = device
        self.model_id = model_id
        self.num_candidates = num_candidates
        
        self.model = None
        self.tokenizer = None
        self._model_loaded = False
    
    def _load_model(self):
        """Load the translation model (kept loaded for performance)."""
        if self._model_loaded and self.model is not None:
            return
        
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Transformers library not available")
        
        # Check if model is downloaded
        model_path = self.model_manager.get_model_path(self.model_id)
        if not model_path:
            logger.info(f"Model {self.model_id} not found, downloading...")
            model_path = self.model_manager.download_model(self.model_id)
        
        # Check memory
        estimated_size = 24.0  # GB for translategemma-12b-it
        if not self.memory_manager.can_load_model(estimated_size):
            available = self.memory_manager.get_available_memory_gb()
            raise RuntimeError(
                f"Insufficient GPU memory: {available:.2f}GB available, "
                f"{estimated_size}GB needed"
            )
        
        try:
            logger.info(f"Loading model {self.model_id}...")
            self.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            self.model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                torch_dtype=torch.float16 if self.device.startswith("cuda") else torch.float32,
                device_map="auto" if self.device.startswith("cuda") else None
            )
            
            if not self.device.startswith("cuda"):
                self.model = self.model.to(self.device)
            
            self.model.eval()
            self._model_loaded = True
            
            # Register with memory manager
            self.memory_manager.register_loaded_model(
                self.model_id, self.model, estimated_size
            )
            
            logger.info(f"Model {self.model_id} loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading model {self.model_id}: {e}")
            raise
    
    @retry_on_error(max_attempts=3, delay=1.0)
    def generate_candidates(self, prompt: str, temperature: float = 0.7,
                           max_length: int = 512) -> List[str]:
        """
        Generate translation candidates from prompt.
        
        Args:
            prompt: Translation prompt
            temperature: Sampling temperature
            max_length: Maximum generation length
        
        Returns:
            List of candidate translations
        """
        if not self._model_loaded:
            self._load_model()
        
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded")
        
        try:
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, 
                                  max_length=1024)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            candidates = []
            
            # Generate multiple candidates with different sampling
            for i in range(self.num_candidates):
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=max_length,
                        temperature=temperature + (i * 0.1),  # Vary temperature slightly
                        do_sample=True,
                        num_return_sequences=1,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                # Decode
                generated_text = self.tokenizer.decode(
                    outputs[0][inputs['input_ids'].shape[1]:],
                    skip_special_tokens=True
                ).strip()
                
                if generated_text and generated_text not in candidates:
                    candidates.append(generated_text)
            
            logger.debug(f"Generated {len(candidates)} candidates")
            return candidates[:self.num_candidates]
            
        except Exception as e:
            logger.error(f"Error generating candidates: {e}")
            raise
