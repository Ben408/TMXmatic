"""
GPU Detection Utilities

Provides GPU capability detection and information retrieval.
"""
import logging
from typing import Optional, Dict, Any
import sys

logger = logging.getLogger(__name__)

class GPUInfo:
    """Information about a GPU."""
    
    def __init__(self, device_id: int, name: str, total_memory_gb: float, 
                 available_memory_gb: float = None):
        self.device_id = device_id
        self.name = name
        self.total_memory_gb = total_memory_gb
        self.available_memory_gb = available_memory_gb
    
    def __repr__(self):
        avail_str = f"{self.available_memory_gb:.2f}" if self.available_memory_gb else "N/A"
        return (f"GPUInfo(device_id={self.device_id}, name='{self.name}', "
                f"total_memory_gb={self.total_memory_gb:.2f}, "
                f"available_memory_gb={avail_str})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'device_id': self.device_id,
            'name': self.name,
            'total_memory_gb': self.total_memory_gb,
            'available_memory_gb': self.available_memory_gb
        }


class GPUDetector:
    """Detects and provides information about available GPUs."""
    
    def __init__(self):
        self._cuda_available = None
        self._gpu_info = None
    
    def is_cuda_available(self) -> bool:
        """
        Check if CUDA is available.
        
        Returns:
            True if CUDA is available, False otherwise.
        """
        if self._cuda_available is not None:
            return self._cuda_available
        
        try:
            import torch
            self._cuda_available = torch.cuda.is_available()
            if self._cuda_available:
                logger.info("CUDA is available")
            else:
                logger.warning("CUDA is not available")
            return self._cuda_available
        except ImportError:
            logger.warning("PyTorch not installed, CUDA check unavailable")
            self._cuda_available = False
            return False
        except Exception as e:
            logger.error(f"Error checking CUDA availability: {e}")
            self._cuda_available = False
            return False
    
    def get_gpu_count(self) -> int:
        """
        Get the number of available GPUs.
        
        Returns:
            Number of GPUs, or 0 if CUDA is not available.
        """
        if not self.is_cuda_available():
            return 0
        
        try:
            import torch
            count = torch.cuda.device_count()
            logger.info(f"Found {count} GPU(s)")
            return count
        except Exception as e:
            logger.error(f"Error getting GPU count: {e}")
            return 0
    
    def get_gpu_info(self, device_id: int = 0) -> Optional[GPUInfo]:
        """
        Get information about a specific GPU.
        
        Args:
            device_id: The GPU device ID (default: 0)
        
        Returns:
            GPUInfo object if GPU is available, None otherwise.
        """
        if not self.is_cuda_available():
            return None
        
        if device_id >= self.get_gpu_count():
            logger.warning(f"GPU device {device_id} not available")
            return None
        
        try:
            import torch
            
            # Get device properties
            props = torch.cuda.get_device_properties(device_id)
            total_memory_bytes = props.total_memory
            total_memory_gb = total_memory_bytes / (1024 ** 3)
            
            # Get available memory
            torch.cuda.set_device(device_id)
            allocated = torch.cuda.memory_allocated(device_id)
            reserved = torch.cuda.memory_reserved(device_id)
            available_memory_bytes = total_memory_bytes - reserved
            available_memory_gb = available_memory_bytes / (1024 ** 3)
            
            gpu_info = GPUInfo(
                device_id=device_id,
                name=props.name,
                total_memory_gb=total_memory_gb,
                available_memory_gb=available_memory_gb
            )
            
            logger.info(f"GPU {device_id}: {gpu_info.name}, "
                       f"{total_memory_gb:.2f}GB total, "
                       f"{available_memory_gb:.2f}GB available")
            
            return gpu_info
            
        except Exception as e:
            logger.error(f"Error getting GPU info for device {device_id}: {e}")
            return None
    
    def get_all_gpus(self) -> list[GPUInfo]:
        """
        Get information about all available GPUs.
        
        Returns:
            List of GPUInfo objects.
        """
        gpus = []
        count = self.get_gpu_count()
        
        for device_id in range(count):
            gpu_info = self.get_gpu_info(device_id)
            if gpu_info:
                gpus.append(gpu_info)
        
        return gpus
    
    def check_gpu_requirements(self, min_memory_gb: float = 8.0) -> tuple[bool, Optional[str]]:
        """
        Check if GPU meets minimum requirements.
        
        Args:
            min_memory_gb: Minimum required GPU memory in GB (default: 8.0)
        
        Returns:
            Tuple of (meets_requirements: bool, error_message: Optional[str])
        """
        if not self.is_cuda_available():
            return False, "CUDA is not available. GPU processing cannot be used."
        
        gpu_count = self.get_gpu_count()
        if gpu_count == 0:
            return False, "No GPUs detected."
        
        # Check first GPU (primary GPU)
        gpu_info = self.get_gpu_info(0)
        if not gpu_info:
            return False, "Could not retrieve GPU information."
        
        if gpu_info.total_memory_gb < min_memory_gb:
            return False, (
                f"GPU memory ({gpu_info.total_memory_gb:.2f}GB) is below "
                f"minimum requirement ({min_memory_gb}GB)."
            )
        
        return True, None
    
    def get_gpu_summary(self) -> Dict[str, Any]:
        """
        Get a summary of GPU capabilities.
        
        Returns:
            Dictionary with GPU summary information.
        """
        summary = {
            'cuda_available': self.is_cuda_available(),
            'gpu_count': self.get_gpu_count(),
            'gpus': []
        }
        
        if summary['cuda_available']:
            gpus = self.get_all_gpus()
            summary['gpus'] = [gpu.to_dict() for gpu in gpus]
        
        return summary


def detect_gpu() -> GPUDetector:
    """
    Convenience function to create and initialize a GPU detector.
    
    Returns:
        GPUDetector instance.
    """
    return GPUDetector()
