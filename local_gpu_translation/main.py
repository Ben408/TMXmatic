"""
Main Entry Point

Command-line interface and main entry point for local GPU translation module.
"""
import argparse
import logging
import sys
from pathlib import Path

from shared.gpu.detector import GPUDetector
from shared.models.model_manager import ModelManager
from shared.models.memory_manager import MemoryManager
from shared.config.profile_manager import ProfileManager
from shared.tqe.tqe import TQEEngine
from local_gpu_translation.llm_translation.translator import Translator
from local_gpu_translation.integration.workflow_manager import WorkflowManager
from shared.utils.logging import setup_logging

logger = setup_logging(level=logging.INFO)


def check_gpu_requirements():
    """Check if GPU requirements are met."""
    detector = GPUDetector()
    if not detector.is_cuda_available():
        logger.warning("CUDA not available, will use CPU (may be slow)")
        return False
    
    gpus = detector.get_gpu_info()
    if not gpus:
        logger.warning("No GPUs detected")
        return False
    
    # Check if any GPU has sufficient memory (8GB minimum)
    for gpu in gpus:
        if gpu.available_memory_gb and gpu.available_memory_gb >= 8.0:
            logger.info(f"GPU detected: {gpu.name} ({gpu.available_memory_gb:.1f}GB available)")
            return True
    
    logger.warning("No GPU with sufficient memory (8GB+) detected")
    return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Local GPU Translation and Quality Estimation for TMXmatic"
    )
    parser.add_argument("--xliff", required=True, help="Input XLIFF file")
    parser.add_argument("--output", required=True, help="Output XLIFF file")
    parser.add_argument("--tmx", help="Optional TMX translation memory file")
    parser.add_argument("--tbx", help="Optional TBX terminology file")
    parser.add_argument("--src-lang", default="en", help="Source language code")
    parser.add_argument("--tgt-lang", default="fr", help="Target language code")
    parser.add_argument("--profile", help="Configuration profile name")
    parser.add_argument("--device", default="cuda", choices=["cpu", "cuda"],
                       help="Device to use")
    parser.add_argument("--num-candidates", type=int, default=5,
                       help="Number of translation candidates to generate")
    parser.add_argument("--batch-size", type=int, default=100,
                       help="Batch size for processing")
    parser.add_argument("--save-interval", type=int, default=50,
                       help="Save partial results every N segments")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check GPU
    if args.device == "cuda":
        check_gpu_requirements()
    
    # Initialize components
    logger.info("Initializing components...")
    model_manager = ModelManager()
    memory_manager = MemoryManager()
    profile_manager = ProfileManager()
    
    # Load profile if specified
    profile = None
    if args.profile:
        profile = profile_manager.get_profile(args.profile)
        if not profile:
            logger.warning(f"Profile '{args.profile}' not found, using defaults")
    
    # Initialize translator
    translator = Translator(
        model_manager, memory_manager,
        device=args.device,
        num_candidates=args.num_candidates
    )
    
    # Initialize TQE engine
    tqe_engine = TQEEngine(device=args.device)
    
    # Create workflow manager
    workflow_manager = WorkflowManager(translator, tqe_engine)
    
    # Setup workflow
    xliff_path = Path(args.xliff)
    tmx_path = Path(args.tmx) if args.tmx else None
    tbx_path = Path(args.tbx) if args.tbx else None
    output_path = Path(args.output)
    
    if not xliff_path.exists():
        logger.error(f"XLIFF file not found: {xliff_path}")
        sys.exit(1)
    
    logger.info("Setting up workflow...")
    workflow_manager.setup_workflow(
        xliff_path, tmx_path, tbx_path,
        args.src_lang, args.tgt_lang
    )
    
    # Process XLIFF
    logger.info("Processing XLIFF...")
    stats = workflow_manager.process_xliff(
        xliff_path, output_path,
        args.src_lang, args.tgt_lang,
        batch_size=args.batch_size,
        save_interval=args.save_interval
    )
    
    logger.info("Processing complete!")
    logger.info(f"Statistics: {stats}")
    logger.info(f"Output saved to: {output_path}")


if __name__ == "__main__":
    main()
