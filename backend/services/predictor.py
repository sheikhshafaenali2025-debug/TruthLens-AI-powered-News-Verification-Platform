"""
services/predictor.py

Loads the trained model + vectorizer exactly once and exposes a fast
predict() method. A module-level singleton is used so Flask (which may
handle many requests per worker) never re-loads the pickle files from disk
per-request.
"""

import json
import os
import time
from typing import Optional

import joblib

from services.preprocessing import clean_text


class ModelNotLoadedError(RuntimeError):
    """Raised when a prediction is requested but no trained model is available."""


class Predictor:
    """Wraps the TF-IDF vectorizer + Logistic Regression model."""

    def __init__(self, config):
        self.config = config
        self.model = None
        self.vectorizer = None
        self.metadata: dict = {}
        self._load()

    def _load(self) -> None:
        """Load model, vectorizer, and metadata from disk if present."""
        if os.path.exists(self.config.MODEL_PATH) and os.path.exists(self.config.VECTORIZER_PATH):
            self.model = joblib.load(self.config.MODEL_PATH)
            self.vectorizer = joblib.load(self.config.VECTORIZER_PATH)
        else:
            self.model = None
            self.vectorizer = None

        if os.path.exists(self.config.METADATA_PATH):
            with open(self.config.METADATA_PATH, "r") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

    def reload(self) -> None:
        """Re-read model artifacts from disk (used after retraining)."""
        self._load()

    @property
    def is_ready(self) -> bool:
        return self.model is not None and self.vectorizer is not None

    def predict(self, text: str) -> dict:
        """
        Run the full inference pipeline on a raw text string.

        Returns a dict with prediction, confidence, real/fake probabilities,
        and processing_time (seconds, float).
        """
        if not self.is_ready:
            raise ModelNotLoadedError(
                "No trained model found. Train one via ml/train_model.py "
                "or POST /api/admin/retrain."
            )

        start = time.perf_counter()

        cleaned = clean_text(text)
        vector = self.vectorizer.transform([cleaned])

        classes = list(self.model.classes_)
        proba = self.model.predict_proba(vector)[0]
        proba_map = {cls: float(p) for cls, p in zip(classes, proba)}

        real_prob = proba_map.get("REAL", 0.0) * 100
        fake_prob = proba_map.get("FAKE", 0.0) * 100

        prediction = "REAL" if real_prob >= fake_prob else "FAKE"
        confidence = max(real_prob, fake_prob)

        elapsed = time.perf_counter() - start

        return {
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "real_probability": round(real_prob, 2),
            "fake_probability": round(fake_prob, 2),
            "processing_time": round(elapsed, 4),
        }


# --- Module-level singleton ---------------------------------------------
_predictor_instance: Optional[Predictor] = None


def get_predictor(config) -> Predictor:
    """Return the process-wide Predictor singleton, creating it on first use."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = Predictor(config)
    return _predictor_instance


def reset_predictor() -> None:
    """Force the next get_predictor() call to reload from disk (post-retrain)."""
    global _predictor_instance
    if _predictor_instance is not None:
        _predictor_instance.reload()
