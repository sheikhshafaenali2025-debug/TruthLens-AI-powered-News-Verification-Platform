"""
config.py
Central configuration for the TruthLens backend.
All tunable settings live here so nothing is hard-coded deep in the app.
"""

import os

# Base directory of the backend package
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Application-wide configuration."""

    # --- Flask ---
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    JSON_SORT_KEYS: bool = False

    # --- Database ---
    DATABASE_DIR: str = os.path.join(BASE_DIR, "database")
    DATABASE_PATH: str = os.path.join(DATABASE_DIR, "history.db")
    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # --- ML artifacts ---
    ML_DIR: str = os.path.join(BASE_DIR, "ml")
    MODEL_PATH: str = os.path.join(ML_DIR, "model.pkl")
    VECTORIZER_PATH: str = os.path.join(ML_DIR, "vectorizer.pkl")
    METADATA_PATH: str = os.path.join(ML_DIR, "model_metadata.json")
    DATASET_PATH: str = os.path.join(ML_DIR, "dataset.csv")

    # --- Validation / limits ---
    MAX_TEXT_LENGTH: int = 20000          # maximum characters accepted in /api/predict
    MIN_TEXT_LENGTH: int = 10             # minimum characters required for a meaningful prediction
    MAX_HISTORY_TEXT_PREVIEW: int = 20000  # stored text is capped at MAX_TEXT_LENGTH already

    # --- CORS ---
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")

    # --- Performance ---
    TARGET_INFERENCE_MS: int = 300
