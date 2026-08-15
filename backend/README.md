# TruthLens Backend

Flask backend that powers AI inference for the TruthLens frontend
(`index.html` / `style.css` / `script.js`, unchanged). This backend only
exposes JSON APIs — it does not serve or modify the frontend.

## Setup

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The server starts on `http://localhost:5000`. A small bootstrap model
(`ml/model.pkl`, `ml/vectorizer.pkl`, trained on `ml/dataset.csv`) ships
with the repo so the API works immediately — swap in a real dataset and
retrain (see below) for production-quality accuracy.

## Training on a real dataset

Replace `ml/dataset.csv` with your own CSV containing `text` and `label`
columns (`label` must be `REAL` or `FAKE`), then either:

```bash
python ml/train_model.py ml/dataset.csv
```

or call the hot-reload endpoint while the server is running:

```bash
curl -X POST http://localhost:5000/api/admin/retrain
```

## API Reference

| Method | Endpoint              | Description                              |
|--------|------------------------|-------------------------------------------|
| POST   | `/api/predict`          | Classify article text as REAL or FAKE     |
| GET    | `/api/history`          | List all stored predictions               |
| DELETE | `/api/history`          | Clear stored predictions                  |
| POST   | `/api/admin/retrain`    | Retrain model from latest dataset, hot-reload |
| GET    | `/api/health`           | Liveness check                            |
| GET    | `/api/model`            | Model metadata (algorithm, accuracy, etc.)|
| GET    | `/api/stats`            | Aggregate prediction statistics           |

### POST /api/predict

Request:
```json
{ "text": "News article text..." }
```

Response:
```json
{
  "prediction": "REAL",
  "confidence": 96.5,
  "probabilities": { "real": 96.5, "fake": 3.5 },
  "processing_time": "0.18 sec"
}
```

## Connecting the existing frontend

`script.js` currently fakes its analysis locally in `analyzeText()`. To
wire it up to this backend, replace that function's call site with a
`fetch("http://localhost:5000/api/predict", { method: "POST", headers: {
"Content-Type": "application/json" }, body: JSON.stringify({ text, source })
})` call and map the JSON response's `prediction`, `confidence`, and
`probabilities` fields onto the existing result-rendering code in
`runResults()`. No HTML/CSS changes are required.

## Project structure

```
backend/
  app.py                 Flask app factory + startup
  config.py               Central configuration
  requirements.txt
  routes/
    prediction.py         /api/predict, /api/health, /api/model, /api/stats
    history.py             /api/history (GET, DELETE)
    admin.py               /api/admin/retrain
  services/
    predictor.py            Singleton model loader + inference
    preprocessing.py        Shared text-cleaning pipeline
  models/
    database.py              SQLAlchemy models (PredictionHistory)
  ml/
    train_model.py           Training script (TF-IDF + LogisticRegression)
    predict.py                 CLI prediction helper
    model.pkl / vectorizer.pkl  Trained artifacts (generated)
    model_metadata.json          Training metadata (generated)
    dataset.csv                    Training data (bootstrap sample included)
  database/
    history.db                 SQLite database (generated on first run)
  utils/
    validators.py               Request validation helpers
```
