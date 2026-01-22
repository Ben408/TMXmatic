"""
COMET Utilities

Helper functions for loading and running COMET models.
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from comet import load_from_checkpoint
    COMET_AVAILABLE = True
except Exception:
    COMET_AVAILABLE = False
    logger.warning("COMET not available")


def load_comet_model(checkpoint_path: str, device: str = "cpu", fp16: bool = False):
    """
    Load COMET model from checkpoint.
    
    Args:
        checkpoint_path: Path to COMET checkpoint
        device: Device to load model on
        fp16: Whether to use half precision
    
    Returns:
        Loaded COMET model
    """
    if not COMET_AVAILABLE:
        raise RuntimeError(
            "COMET python package not available. "
            "Install from https://github.com/Unbabel/COMET.git"
        )
    
    model = load_from_checkpoint(checkpoint_path)
    if device.startswith("cuda"):
        model = model.to(device)
        if fp16:
            try:
                model.half()
            except Exception:
                # Some PL wrappers may not accept .half()
                logger.warning("Could not convert COMET model to fp16")
                pass
    
    logger.info(f"Loaded COMET model from {checkpoint_path}")
    return model


def run_comet_ref_batch(comet_model, srcs: List[str], hyps: List[str], refs: List[str],
                        batch_size: int = 16, device: str = "cuda") -> List[float]:
    """
    Run COMET reference-based scoring on a batch.
    
    Args:
        comet_model: Loaded COMET model
        srcs: List of source texts
        hyps: List of hypothesis translations
        refs: List of reference translations
        batch_size: Batch size for processing
        device: Device to use
    
    Returns:
        List of scores
    """
    results = []
    for i in range(0, len(srcs), batch_size):
        b_src = srcs[i:i+batch_size]
        b_hyp = hyps[i:i+batch_size]
        b_ref = refs[i:i+batch_size]
        
        try:
            # COMET's predict API
            pred = comet_model.predict(
                b_src, b_hyp, b_ref,
                batch_size=len(b_src),
                gpus=1 if device.startswith("cuda") else 0
            )
            
            for p in pred:
                val = None
                if isinstance(p, dict):
                    for k in ("score", "preds", "pred"):
                        if k in p:
                            val = p[k]
                            break
                if val is None:
                    try:
                        val = float(p)
                    except Exception:
                        val = 0.0
                results.append(float(val))
        except Exception as e:
            logger.error(f"Error in COMET ref batch: {e}")
            # Add default scores for failed batch
            results.extend([0.0] * len(b_src))
    
    return results


def run_comet_qe_batch(comet_qe_model, srcs: List[str], hyps: List[str],
                       batch_size: int = 16, device: str = "cuda") -> List[float]:
    """
    Run COMET-QE (quality estimation, no reference) on a batch.
    
    Args:
        comet_qe_model: Loaded COMET-QE model
        srcs: List of source texts
        hyps: List of hypothesis translations
        batch_size: Batch size for processing
        device: Device to use
    
    Returns:
        List of scores
    """
    results = []
    for i in range(0, len(srcs), batch_size):
        b_src = srcs[i:i+batch_size]
        b_hyp = hyps[i:i+batch_size]
        
        try:
            pred = comet_qe_model.predict(
                b_src, b_hyp,
                batch_size=len(b_src),
                gpus=1 if device.startswith("cuda") else 0
            )
            
            for p in pred:
                val = None
                if isinstance(p, dict):
                    for k in ("score", "preds", "pred"):
                        if k in p:
                            val = p[k]
                            break
                if val is None:
                    try:
                        val = float(p)
                    except Exception:
                        val = 0.0
                results.append(float(val))
        except Exception as e:
            logger.error(f"Error in COMET-QE batch: {e}")
            # Add default scores for failed batch
            results.extend([0.0] * len(b_src))
    
    return results
