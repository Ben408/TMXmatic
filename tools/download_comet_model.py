#!/usr/bin/env python3
"""
Helper to download COMET model files from the Hugging Face Hub.
Example:
 python tools/download_comet_model.py --repo_id Unbabel/wmt22-comet-da --out_dir models/comet-da
"""
import argparse
import os
from huggingface_hub import hf_hub_download, list_repo_files

def download(repo_id: str, out_dir: str, filename_hint: Optional[str] = None):
    os.makedirs(out_dir, exist_ok=True)
    print("Listing files in repo:", repo_id)
    files = list_repo_files(repo_id)
    # Heuristic: choose a checkpoint file with 'best' or 'checkpoint' in its name
    candidate_files = [f for f in files if any(tok in f.lower() for tok in ("best", "checkpoint", ".pt", ".bin", "pytorch"))]
    chosen = None
    if filename_hint:
        for f in candidate_files:
            if filename_hint in f:
                chosen = f
                break
    if chosen is None and candidate_files:
        # prefer names containing 'best'
        bests = [f for f in candidate_files if "best" in f.lower()]
        chosen = bests[0] if bests else candidate_files[0]
    if chosen is None:
        raise RuntimeError(f"No checkpoint-like file found in repo {repo_id}. Available: {files}")
    print("Downloading", chosen)
    path = hf_hub_download(repo_id=repo_id, filename=chosen)
    dest = os.path.join(out_dir, os.path.basename(path))
    import shutil
    shutil.copy(path, dest)
    print("Saved model to", dest)
    return dest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo_id", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--filename_hint", default=None)
    args = parser.parse_args()
    download(args.repo_id, args.out_dir, args.filename_hint)