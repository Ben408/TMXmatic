"""
TQE Scoring Primitives

Core scoring functions for translation quality estimation.
"""
import logging
import math
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional libs
try:
    from bert_score import score as bert_score
    BERTSCORE_AVAILABLE = True
except Exception:
    BERTSCORE_AVAILABLE = False
    logger.warning("BERTScore not available")

try:
    from sentence_transformers import SentenceTransformer, util as st_util
    SBERT_AVAILABLE = True
except Exception:
    SBERT_AVAILABLE = False
    logger.warning("SentenceTransformers not available")

try:
    import torch
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("PyTorch/Transformers not available")


def compute_accuracy_with_reference_bertscore(candidate: str, reference: str, lang: str = "en") -> float:
    """
    Compute accuracy score using BERTScore with reference.
    
    Args:
        candidate: Candidate translation
        reference: Reference translation
        lang: Language code
    
    Returns:
        Accuracy score (0-100)
    """
    if BERTSCORE_AVAILABLE:
        model_type = "xlm-roberta-large" if lang != "en" else "roberta-large"
        try:
            P, R, F1 = bert_score([candidate], [reference], lang=lang, 
                                 model_type=model_type, rescale_with_baseline=True)
            val = float(F1[0])
            return val * 100.0
        except Exception as e:
            logger.warning(f"BERTScore computation failed: {e}")
            return 50.0
    elif SBERT_AVAILABLE:
        try:
            sbert = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
            emb_c = sbert.encode(candidate, convert_to_tensor=True)
            emb_r = sbert.encode(reference, convert_to_tensor=True)
            sim = float(st_util.cos_sim(emb_c, emb_r))
            return max(0.0, min(100.0, sim * 100.0))
        except Exception as e:
            logger.warning(f"SBERT computation failed: {e}")
            return 50.0
    else:
        logger.warning("No accuracy scoring method available, returning default")
        return 50.0


def compute_accuracy_without_reference_sbert(src: str, candidate: str) -> float:
    """
    Compute accuracy score using SBERT without reference.
    
    Args:
        src: Source text
        candidate: Candidate translation
    
    Returns:
        Accuracy score (0-100)
    """
    if SBERT_AVAILABLE:
        try:
            sbert = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
            emb_src = sbert.encode(src, convert_to_tensor=True)
            emb_c = sbert.encode(candidate, convert_to_tensor=True)
            sim = float(st_util.cos_sim(emb_src, emb_c))
            score = max(0.0, min(100.0, (sim + 1.0) / 2.0 * 100.0))
            return score
        except Exception as e:
            logger.warning(f"SBERT computation failed: {e}")
            return 50.0
    else:
        logger.warning("SBERT not available, returning default")
        return 50.0


def compute_fluency_perplexity(candidate: str, lm_model=None, lm_tokenizer=None, device="cpu") -> float:
    """
    Compute fluency score using language model perplexity.
    
    Args:
        candidate: Candidate translation
        lm_model: Language model
        lm_tokenizer: Tokenizer
        device: Device to use
    
    Returns:
        Fluency score (0-100)
    """
    if not TRANSFORMERS_AVAILABLE or lm_model is None or lm_tokenizer is None:
        return 50.0
    
    try:
        lm_model.eval()
        with torch.no_grad():
            inputs = lm_tokenizer(candidate, return_tensors="pt", truncation=True, max_length=1024)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            labels = inputs["input_ids"]
            outputs = lm_model(**inputs, labels=labels)
            loss = float(outputs.loss)
        ppl = math.exp(min(loss, 50))
        score = 100.0 * (1.0 - math.tanh(math.log(max(ppl, 1.0)) / 1.5))
        return max(0.0, min(100.0, score))
    except Exception as e:
        logger.warning(f"Fluency computation failed: {e}")
        return 50.0


def compute_tone_score(candidate: str, tone_exemplars: List[str], sbert_model=None) -> float:
    """
    Compute tone score by comparing with exemplars.
    
    Args:
        candidate: Candidate translation
        tone_exemplars: List of tone exemplar texts
        sbert_model: SBERT model for encoding
    
    Returns:
        Tone score (0-100)
    """
    if not SBERT_AVAILABLE or sbert_model is None:
        return 50.0
    
    try:
        emb_c = sbert_model.encode(candidate, convert_to_tensor=True)
        sims = []
        for ex in tone_exemplars:
            emb_e = sbert_model.encode(ex, convert_to_tensor=True)
            sims.append(float(st_util.cos_sim(emb_c, emb_e)))
        if not sims:
            return 50.0
        avg_sim = sum(sims) / len(sims)
        return max(0.0, min(100.0, (avg_sim + 1.0) / 2.0 * 100.0))
    except Exception as e:
        logger.warning(f"Tone computation failed: {e}")
        return 50.0


def aggregate_scores(acc: float, flu: float, tone: float, uq_halluc: bool = False,
                     weights: Tuple[float, float, float] = (0.6, 0.25, 0.15)) -> Tuple[float, str]:
    """
    Aggregate individual scores into weighted score and decision.
    
    Args:
        acc: Accuracy score
        flu: Fluency score
        tone: Tone score
        uq_halluc: Whether UQLM detected hallucination
        weights: Weights for (accuracy, fluency, tone)
    
    Returns:
        Tuple of (weighted_score, decision)
    """
    w_acc, w_flu, w_tone = weights
    weighted = w_acc * acc + w_flu * flu + w_tone * tone
    
    if uq_halluc:
        return weighted, "needs_human_revision"
    if weighted >= 85.0:
        return weighted, "accept_auto"
    if weighted >= 70.0:
        return weighted, "accept_with_review"
    return weighted, "needs_human_revision"


def normalize_comet_score(raw_score: float, raw_min: float = -1.0, raw_max: float = 1.0) -> float:
    """
    Normalize COMET score to 0-100 range.
    
    Args:
        raw_score: Raw COMET score
        raw_min: Minimum raw score
        raw_max: Maximum raw score
    
    Returns:
        Normalized score (0-100)
    """
    if raw_max == raw_min:
        return max(0.0, min(100.0, raw_score))
    norm = (raw_score - raw_min) / (raw_max - raw_min)
    return max(0.0, min(100.0, norm * 100.0))
