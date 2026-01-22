"""
GPU Memory Management

Handles GPU memory monitoring, batch size adjustment, and memory optimization.
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """GPU memory statistics."""
    total_memory_gb: float
    allocated_memory_gb: float
    reserved_memory_gb: float
    free_memory_gb: float
    utilization_percent: float


class MemoryManager:
    """
    Manages GPU memory for model loading and inference.
    
    Key features:
    - Monitor GPU memory usage
    - Dynamic batch size adjustment based on available memory
    - Keep models loaded for performance (as per requirements)
    - Handle OOM (Out of Memory) situations gracefully
    """
    
    def __init__(self, device_id: int = 0, safety_margin_gb: float = 1.0):
        """
        Initialize MemoryManager.
        
        Args:
            device_id: GPU device ID (default: 0)
            safety_margin_gb: Safety margin in GB to reserve (default: 1.0GB)
        """
        self.device_id = device_id
        self.safety_margin_gb = safety_margin_gb
        self._loaded_models: Dict[str, Any] = {}  # Track loaded models
        
    def get_memory_stats(self) -> Optional[MemoryStats]:
        """
        Get current GPU memory statistics.
        
        Returns:
            MemoryStats object if GPU is available, None otherwise
        """
        try:
            import torch
            
            if not torch.cuda.is_available():
                logger.warning("CUDA is not available")
                return None
            
            if self.device_id >= torch.cuda.device_count():
                logger.warning(f"GPU device {self.device_id} not available")
                return None
            
            torch.cuda.set_device(self.device_id)
            
            # Get device properties
            props = torch.cuda.get_device_properties(self.device_id)
            total_memory_bytes = props.total_memory
            total_memory_gb = total_memory_bytes / (1024 ** 3)
            
            # Get current memory usage
            allocated_bytes = torch.cuda.memory_allocated(self.device_id)
            reserved_bytes = torch.cuda.memory_reserved(self.device_id)
            
            allocated_gb = allocated_bytes / (1024 ** 3)
            reserved_gb = reserved_bytes / (1024 ** 3)
            free_gb = total_memory_gb - reserved_gb
            
            utilization_percent = (reserved_gb / total_memory_gb) * 100 if total_memory_gb > 0 else 0
            
            return MemoryStats(
                total_memory_gb=total_memory_gb,
                allocated_memory_gb=allocated_gb,
                reserved_memory_gb=reserved_gb,
                free_memory_gb=free_gb,
                utilization_percent=utilization_percent
            )
            
        except ImportError:
            logger.warning("PyTorch not available for memory monitoring")
            return None
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return None
    
    def get_available_memory_gb(self) -> Optional[float]:
        """
        Get available GPU memory in GB.
        
        Returns:
            Available memory in GB, or None if unavailable
        """
        stats = self.get_memory_stats()
        if stats is None:
            return None
        
        # Subtract safety margin
        available = stats.free_memory_gb - self.safety_margin_gb
        return max(0.0, available)
    
    def can_load_model(self, estimated_size_gb: float) -> bool:
        """
        Check if a model can be loaded given current memory usage.
        
        Args:
            estimated_size_gb: Estimated model size in GB
        
        Returns:
            True if model can be loaded, False otherwise
        """
        available = self.get_available_memory_gb()
        if available is None:
            return False
        
        return available >= estimated_size_gb
    
    def register_loaded_model(self, model_id: str, model: Any, estimated_size_gb: float):
        """
        Register a loaded model for tracking.
        
        Args:
            model_id: Model identifier
            model: The loaded model object
            estimated_size_gb: Estimated model size in GB
        """
        self._loaded_models[model_id] = {
            'model': model,
            'estimated_size_gb': estimated_size_gb
        }
        logger.info(f"Registered loaded model: {model_id} ({estimated_size_gb:.2f}GB)")
    
    def unregister_model(self, model_id: str):
        """
        Unregister a model (model should be unloaded separately).
        
        Args:
            model_id: Model identifier
        """
        if model_id in self._loaded_models:
            del self._loaded_models[model_id]
            logger.info(f"Unregistered model: {model_id}")
    
    def get_loaded_models(self) -> List[str]:
        """
        Get list of currently loaded model IDs.
        
        Returns:
            List of model IDs
        """
        return list(self._loaded_models.keys())
    
    def calculate_optimal_batch_size(self, base_batch_size: int = 1, 
                                     memory_per_item_mb: float = 100.0) -> int:
        """
        Calculate optimal batch size based on available memory.
        
        Args:
            base_batch_size: Base batch size to start with
            memory_per_item_mb: Estimated memory per item in MB
        
        Returns:
            Optimal batch size
        """
        available = self.get_available_memory_gb()
        if available is None:
            logger.warning("Cannot calculate batch size: GPU memory unavailable")
            return base_batch_size
        
        # Convert available memory to MB
        available_mb = available * 1024
        
        # Calculate how many items we can fit
        # Reserve some memory for overhead
        usable_memory_mb = available_mb * 0.8  # Use 80% of available
        
        max_items = int(usable_memory_mb / memory_per_item_mb)
        
        # Use the larger of base_batch_size or calculated max, but don't exceed max_items
        optimal = max(base_batch_size, min(max_items, base_batch_size * 4))
        
        logger.debug(f"Optimal batch size: {optimal} (available: {available:.2f}GB, "
                   f"per item: {memory_per_item_mb}MB)")
        
        return optimal
    
    def check_oom_risk(self, additional_memory_gb: float = 0.0) -> tuple[bool, Optional[str]]:
        """
        Check if there's a risk of OOM with additional memory usage.
        
        Args:
            additional_memory_gb: Additional memory that will be used
        
        Returns:
            Tuple of (is_safe: bool, warning_message: Optional[str])
        """
        available = self.get_available_memory_gb()
        if available is None:
            return False, "GPU memory unavailable"
        
        if available < additional_memory_gb:
            return False, (
                f"Insufficient memory: {available:.2f}GB available, "
                f"{additional_memory_gb:.2f}GB needed"
            )
        
        # Warn if memory usage would exceed 90%
        stats = self.get_memory_stats()
        if stats:
            projected_usage = (stats.reserved_memory_gb + additional_memory_gb) / stats.total_memory_gb
            if projected_usage > 0.9:
                return True, (
                    f"High memory usage warning: {projected_usage*100:.1f}% "
                    f"of GPU memory will be used"
                )
        
        return True, None
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of GPU memory status.
        
        Returns:
            Dictionary with memory summary information
        """
        stats = self.get_memory_stats()
        if stats is None:
            return {
                'available': False,
                'error': 'GPU memory unavailable'
            }
        
        return {
            'available': True,
            'device_id': self.device_id,
            'total_memory_gb': stats.total_memory_gb,
            'allocated_memory_gb': stats.allocated_memory_gb,
            'reserved_memory_gb': stats.reserved_memory_gb,
            'free_memory_gb': stats.free_memory_gb,
            'available_memory_gb': self.get_available_memory_gb(),
            'utilization_percent': stats.utilization_percent,
            'loaded_models': self.get_loaded_models(),
            'loaded_model_count': len(self._loaded_models)
        }
