#!/usr/bin/env python3
"""
tools/calibrate.py

Fit calibration mappings (isotonic regression) for raw model outputs -> human scores.
Input CSV columns (example): tu_id, human_accuracy, comet_raw, berts, fluency_raw, tone_raw
Outputs a JSON file with per-metric calibrators (sklearn IsotonicRegression), stored as sampling mapping
(we save the fitted mapping as arrays for lookup).

Usage:
 python tools/calibrate.py --input calibration.csv --out calib.json
"""
import argparse
import csv
import json
import numpy as np
from collections import defaultdict

try:
    from sklearn.isotonic import IsotonicRegression
except Exception:
    IsotonicRegression = None

def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)
    return rows

def fit_isotonic(x, y):
    if IsotonicRegression is None:
        raise RuntimeError("scikit-learn required for calibration")
    ir = IsotonicRegression(out_of_bounds="clip")
    ir.fit(x, y)
    # we'll store the x_thresholds and y_thresholds (the piecewise mapping points)
    xp = ir.X_thresholds_.tolist()
    yp = ir.y_thresholds_.tolist()
    return {"x": xp, "y": yp}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV with human and raw scores")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    rows = load_csv(args.input)
    # collect arrays for each metric
    metrics = defaultdict(list)
    human = []
    for r in rows:
        human.append(float(r.get("human_score") or r.get("human_accuracy") or r.get("human") or 0.0))
        for k,v in r.items():
            if k.startswith("raw_") or k in ("comet_raw","berts","fluency_raw","tone_raw"):
                try:
                    metrics[k].append(float(v))
                except:
                    metrics[k].append(0.0)
    human = np.array(human)
    out = {}
    for k,vals in metrics.items():
        x = np.array(vals)
        try:
            mapping = fit_isotonic(x, human)
            out[k] = mapping
        except Exception as e:
            print("Could not fit", k, e)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print("Saved calibration to", args.out)

if __name__ == "__main__":
    main()