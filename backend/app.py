"""
app.py

TruthLens backend entry point.

Run with:
    python app.py

Exposes REST APIs consumed by the existing TruthLens frontend
(index.html / style.css / script.js). This process only serves JSON APIs;
it does not render or modify the frontend in any way.
"""

import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from models.database import init_db
from routes.admin import admin_bp
from routes.history import history_bp
from routes.prediction import prediction_bp
from services.predictor import get_predictor


def create_app() -> Flask:
    """Application factory: builds and configures the Flask app."""
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    cfg = Config()

    # Make both the raw Config object (for services that need file paths)
    # and its values (for Flask's own config lookups) available.
    app.config["APP_CONFIG"] = cfg
    app.config["SQLALCHEMY_DATABASE_URI"] = cfg.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = cfg.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["MAX_TEXT_LENGTH"] = cfg.MAX_TEXT_LENGTH
    app.config["MIN_TEXT_LENGTH"] = cfg.MIN_TEXT_LENGTH

    # Ensure required directories exist before anything touches disk.
    os.makedirs(cfg.DATABASE_DIR, exist_ok=True)
    os.makedirs(cfg.ML_DIR, exist_ok=True)

    # --- CORS: allow the static frontend (served from any origin/file) to call us ---
    CORS(app, resources={r"/api/*": {"origins": cfg.CORS_ORIGINS}})

    # --- Database ---
    init_db(app)

    # --- Blueprints ---
    app.register_blueprint(prediction_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(admin_bp)

    # --- Frontend Root Route ---
    @app.route("/")
    def serve_frontend():
        return send_from_directory(frontend_dir, "index.html")

    # --- Load (or lazily prepare to load) the ML model once at startup ---
    with app.app_context():
        predictor = get_predictor(cfg)
        if not predictor.is_ready:
            app.logger.warning(
                "No trained model found at startup. "
                "Run `python ml/train_model.py` or call POST /api/admin/retrain."
            )

    register_error_handlers(app)
    return app


def register_error_handlers(app: Flask) -> None:
    """Centralized JSON error handlers so the API never leaks HTML error pages."""

    @app.errorhandler(400)
    def bad_request(err):
        return jsonify({"error": "Bad request.", "detail": str(err)}), 400

    @app.errorhandler(404)
    def not_found(err):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(err):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(413)
    def payload_too_large(err):
        return jsonify({"error": "Payload too large."}), 413

    @app.errorhandler(500)
    def internal_error(err):
        app.logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error."}), 500


app = create_app()

if __name__ == "__main__":
    # Debug mode is controlled via the FLASK_DEBUG env var (see config.py).
    app.run(host="0.0.0.0", port=5000, debug=app.config["APP_CONFIG"].DEBUG)
