"""
routes/admin.py

POST /api/admin/retrain -- retrain the model from the latest dataset on
                            disk and hot-reload it into the running app,
                            with no Flask restart required.
"""

import os

from flask import Blueprint, current_app, jsonify

from ml.train_model import train
from services.predictor import reset_predictor

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/api/admin/retrain", methods=["POST"])
def retrain():
    """Retrain the classifier and hot-swap the in-memory model."""
    cfg = current_app.config["APP_CONFIG"]

    if not os.path.exists(cfg.DATASET_PATH):
        return jsonify({
            "error": "Dataset not found.",
            "detail": f"Expected a dataset at {cfg.DATASET_PATH}.",
        }), 404

    try:
        metadata = train(cfg.DATASET_PATH)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Retraining failed")
        return jsonify({"error": "Retraining failed.", "detail": str(exc)}), 500

    # Reload the singleton predictor in-place so new requests use the fresh model.
    reset_predictor()

    return jsonify({
        "message": "Model retrained and reloaded successfully.",
        "metadata": metadata,
    }), 200
