import pickle
from pathlib import Path

from sklearn.pipeline import Pipeline
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

import sys
import os
sys.path.append(str(Path(__file__).resolve().parent.parent))
from ml.feature_extractor import feature_names

MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "models"

def main():
    print("Loading Pickled Scikit-Learn Models...")
    try:
        with open(MODEL_DIR / "pattern_model.pkl", "rb") as f:
            model = pickle.load(f)
        with open(MODEL_DIR / "pattern_scaler.pkl", "rb") as f:
            scaler = pickle.load(f)
    except FileNotFoundError:
        print("Model files not found. Skipping ONNX conversion.")
        return

    # Create a pipeline to merge scaling and inference natively in C++ space via ONNX
    pipe = Pipeline([("scaler", scaler), ("rf", model)])

    # Convert to ONNX
    num_features = len(feature_names())
    initial_type = [('float_input', FloatTensorType([None, num_features]))]
    
    # Convert and disable zipmap so we get raw generic tensors back instead of list-of-dicts
    print(f"Converting pipeline. Shape Expected: (None, {num_features})")
    onx = convert_sklearn(pipe, initial_types=initial_type, options={'rf': {'zipmap': False}})

    # Save to disk
    out_path = MODEL_DIR / "pattern_pipeline.onnx"
    with open(out_path, "wb") as f:
        f.write(onx.SerializeToString())
        
    print(f"Optimization complete: {out_path.name} generated successfully! Size: {out_path.stat().st_size} bytes.")

if __name__ == "__main__":
    main()
