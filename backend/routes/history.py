"""
routes/history.py

GET    /api/history -- return all stored predictions (most recent first).
DELETE /api/history -- clear all stored predictions.
"""

from flask import Blueprint, current_app, jsonify

from models.database import PredictionHistory, db

history_bp = Blueprint("history", __name__)


@history_bp.route("/api/history", methods=["GET"])
def get_history():
    """Return every stored prediction, newest first."""
    try:
        records = PredictionHistory.query.order_by(PredictionHistory.created_at.desc()).all()
        return jsonify({
            "count": len(records),
            "history": [r.to_dict() for r in records],
        }), 200
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Failed to fetch history")
        return jsonify({"error": "Could not retrieve history.", "detail": str(exc)}), 500


@history_bp.route("/api/history", methods=["DELETE"])
def clear_history():
    """Delete every stored prediction."""
    try:
        deleted = db.session.query(PredictionHistory).delete()
        db.session.commit()
        return jsonify({"message": "History cleared.", "deleted": deleted}), 200
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("Failed to clear history")
        return jsonify({"error": "Could not clear history.", "detail": str(exc)}), 500
