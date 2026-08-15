"""
routes/prediction.py

POST /api/predict  -- run inference on submitted article text and log it
                       to the history table.
GET  /api/health    -- simple liveness check.
GET  /api/model      -- model metadata (algorithm, training date, accuracy, dataset size).
GET  /api/stats      -- aggregate prediction statistics.
"""

from flask import Blueprint, current_app, jsonify, request

from models.database import PredictionHistory, db
from services.predictor import ModelNotLoadedError, get_predictor
from utils.validators import validate_predict_payload

prediction_bp = Blueprint("prediction", __name__)


@prediction_bp.route("/api/predict", methods=["POST"])
def predict():
    """Accept raw article text and return a REAL/FAKE verdict with probabilities."""
    payload = request.get_json(silent=True)

    cfg = current_app.config
    is_valid, error = validate_predict_payload(
        payload, max_len=cfg["MAX_TEXT_LENGTH"], min_len=cfg["MIN_TEXT_LENGTH"]
    )
    if not is_valid:
        return jsonify({"error": error}), 400

    text = payload["text"].strip()

    try:
        predictor = get_predictor(cfg["APP_CONFIG"])
        result = predictor.predict(text)
    except ModelNotLoadedError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:  # noqa: BLE001 - surface as a clean 500 to the client
        current_app.logger.exception("Prediction failed")
        return jsonify({"error": "Prediction failed.", "detail": str(exc)}), 500

    # Persist to history (best-effort: prediction still returns even if this fails)
    try:
        record = PredictionHistory(
            news_text=text,
            prediction=result["prediction"],
            confidence=result["confidence"],
            real_probability=result["real_probability"],
            fake_probability=result["fake_probability"],
        )
        db.session.add(record)
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("Failed to write prediction to history")

    response = {
        "prediction": result["prediction"],
        "confidence": result["confidence"],
        "probabilities": {
            "real": result["real_probability"],
            "fake": result["fake_probability"],
        },
        "processing_time": f"{result['processing_time']:.2f} sec",
    }
    return jsonify(response), 200


@prediction_bp.route("/api/health", methods=["GET"])
def health():
    """Liveness probe."""
    return jsonify({"status": "healthy"}), 200


@prediction_bp.route("/api/model", methods=["GET"])
def model_info():
    """Return metadata about the currently loaded model."""
    predictor = get_predictor(current_app.config["APP_CONFIG"])

    if not predictor.is_ready:
        return jsonify({"error": "No trained model is currently loaded."}), 503

    metadata = predictor.metadata or {}
    return jsonify({
        "algorithm": metadata.get("algorithm", "TF-IDF + Logistic Regression"),
        "training_date": metadata.get("training_date"),
        "accuracy": metadata.get("accuracy"),
        "dataset_size": metadata.get("dataset_size"),
    }), 200


@prediction_bp.route("/api/stats", methods=["GET"])
def stats():
    """Return aggregate statistics across all stored predictions."""
    total = PredictionHistory.query.count()
    real_count = PredictionHistory.query.filter_by(prediction="REAL").count()
    fake_count = PredictionHistory.query.filter_by(prediction="FAKE").count()

    if total > 0:
        avg_confidence = db.session.query(
            db.func.avg(PredictionHistory.confidence)
        ).scalar() or 0.0
    else:
        avg_confidence = 0.0

    return jsonify({
        "total_predictions": total,
        "real_predictions": real_count,
        "fake_predictions": fake_count,
        "average_confidence": round(float(avg_confidence), 2),
    }), 200
