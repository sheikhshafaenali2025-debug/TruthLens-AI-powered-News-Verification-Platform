"""
models/database.py

SQLAlchemy setup and ORM models for TruthLens.
Single `db` instance is created here and initialized against the Flask
app in app.py (the standard Flask-SQLAlchemy application-factory pattern).
"""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class PredictionHistory(db.Model):
    """One row per /api/predict call."""

    __tablename__ = "prediction_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    news_text = db.Column(db.Text, nullable=False)
    prediction = db.Column(db.String(10), nullable=False)  # 'REAL' or 'FAKE'
    confidence = db.Column(db.Float, nullable=False)
    real_probability = db.Column(db.Float, nullable=False)
    fake_probability = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        """Serialize the row for JSON API responses."""
        return {
            "id": self.id,
            "news_text": self.news_text,
            "prediction": self.prediction,
            "confidence": round(self.confidence, 2),
            "real_probability": round(self.real_probability, 2),
            "fake_probability": round(self.fake_probability, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def init_db(app) -> None:
    """Bind SQLAlchemy to the Flask app and create tables if missing."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
