"""
ml/train_model.py

Trains the TruthLens fake-news classifier:
    TF-IDF Vectorizer + Logistic Regression

Usage:
    python ml/train_model.py [path_to_dataset.csv]

The dataset must be a CSV with at least two columns: "text" and "label",
where label is one of {"REAL", "FAKE"} (case-insensitive).

Saves:
    ml/model.pkl
    ml/vectorizer.pkl
    ml/model_metadata.json   (algorithm, training date, accuracy, dataset size)

If no dataset is found, a small synthetic bootstrap dataset is generated
so the app has a working model out of the box. Replace ml/dataset.csv with
real data and re-run this script (or call POST /api/admin/retrain) for a
production-quality model.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer

# Allow running this file directly (python ml/train_model.py) as well as
# as part of the package (python -m ml.train_model).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.preprocessing import clean_text  # noqa: E402
from config import Config  # noqa: E402


def _bootstrap_dataset() -> pd.DataFrame:
    """
    Generate a small, hand-written synthetic dataset so the backend is
    runnable immediately without requiring an external dataset download.
    This is NOT a substitute for a real training corpus -- swap in a real
    dataset at ml/dataset.csv and retrain for meaningful accuracy.
    """
    real_samples = [
        "The Ministry of Health confirmed on Tuesday that vaccination rates have risen by 12 percent according to official data.",
        "Reuters reported that the central bank raised interest rates by a quarter point, citing inflation concerns.",
        "According to a study published in the journal Nature, researchers found a measurable decline in Arctic sea ice.",
        "City officials announced a new public transit line will open next spring after the council approved funding.",
        "The company's quarterly earnings report showed a 4 percent increase in revenue, in line with analyst expectations.",
        "Officials said the investigation into the bridge collapse is ongoing and a preliminary report is expected next month.",
        "The university's admissions office confirmed applications rose this year following a change to the application process.",
        "A spokesperson for the department stated that road repairs will begin on Monday and continue through the summer.",
        "The World Health Organization released updated guidelines based on data collected from clinical trials.",
        "Local election officials reported voter turnout increased compared with the previous cycle, per certified results.",
        "The national weather service issued an advisory citing data from satellite monitoring of the storm system.",
        "Court documents show the case was filed after a review by the state attorney general's office.",
        "The census bureau published figures indicating population growth slowed slightly over the past decade.",
        "Company executives confirmed the merger during a press conference, pending regulatory approval.",
        "The agriculture department reported crop yields were consistent with the five-year average this season.",
    ]

    fake_samples = [
        "You won't believe what doctors don't want you to know about this miracle cure that big pharma is hiding!",
        "SHOCKING: Secret government files EXPOSED reveal the truth they don't want you to see, anonymous sources say.",
        "Scientists BANNED from revealing this one weird trick that instantly cures everything, click here now!",
        "Anonymous insiders claim the entire election was rigged in a secret conspiracy nobody is talking about.",
        "This celebrity was secretly replaced by a clone and nobody in the mainstream media will report it!!!",
        "The government is hiding aliens in a secret base and refuses to let anyone investigate, sources claim.",
        "Doctors HATE this simple trick that melts fat overnight, banned in several countries for being too effective.",
        "BREAKING: Secret cabal caught on tape admitting to controlling the world's food supply, share before it's deleted!",
        "You won't believe this shocking secret about your water supply that they don't want you to know.",
        "Exclusive: anonymous whistleblower reveals the miracle vaccine cover-up nobody dares to talk about.",
        "This one weird trick banned by big tech will change your life forever, they don't want you to see it!",
        "Secret society exposed for controlling world governments, mainstream media refuses to cover the story.",
        "Shocking conspiracy uncovered: officials secretly banned this cure because it threatens their profits.",
        "Anonymous sources say the moon landing was completely fabricated in a secret studio, exposed at last.",
        "Click here to see the miracle remedy doctors are desperately trying to keep hidden from the public!",
    ]

    data = (
        [{"text": t, "label": "REAL"} for t in real_samples]
        + [{"text": t, "label": "FAKE"} for t in fake_samples]
    )
    return pd.DataFrame(data)


def load_dataset(dataset_path: str) -> pd.DataFrame:
    """Load the training dataset from CSV, falling back to a bootstrap set."""
    if os.path.exists(dataset_path):
        df = pd.read_csv(dataset_path)
        if "text" not in df.columns or "label" not in df.columns:
            raise ValueError("Dataset must contain 'text' and 'label' columns.")
        df = df.dropna(subset=["text", "label"])
        df["label"] = df["label"].astype(str).str.upper().str.strip()
        df = df[df["label"].isin(["REAL", "FAKE"])]
        if len(df) < 10:
            print("Dataset too small after cleaning; using bootstrap dataset instead.")
            return _bootstrap_dataset()
        return df.reset_index(drop=True)

    print(f"No dataset found at {dataset_path}; generating a small bootstrap dataset.")
    df = _bootstrap_dataset()
    os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
    df.to_csv(dataset_path, index=False)
    return df


def train(dataset_path: str = None) -> dict:
    """Run the full training pipeline and persist artifacts. Returns metadata dict."""
    cfg = Config()
    dataset_path = dataset_path or cfg.DATASET_PATH
    os.makedirs(cfg.ML_DIR, exist_ok=True)

    print("Loading dataset...")
    df = load_dataset(dataset_path)
    print(f"Dataset size: {len(df)} rows")

    print("Cleaning text...")
    df["clean_text"] = df["text"].astype(str).apply(clean_text)

    # Guard against a dataset with only one class (can't train/evaluate meaningfully).
    if df["label"].nunique() < 2:
        raise ValueError("Dataset must contain both REAL and FAKE examples.")

    x = df["clean_text"]
    y = df["label"]

    stratify = y if y.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=stratify
    )

    print("Vectorizing (TF-IDF)...")
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    x_train_vec = vectorizer.fit_transform(x_train)
    x_test_vec = vectorizer.transform(x_test)

    print("Training Logistic Regression...")
    model = LogisticRegression(max_iter=1000, C=1.0)
    model.fit(x_train_vec, y_train)

    print("Evaluating...")
    predictions = model.predict(x_test_vec)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Accuracy: {accuracy:.4f}")

    print("Saving artifacts...")
    joblib.dump(model, cfg.MODEL_PATH)
    joblib.dump(vectorizer, cfg.VECTORIZER_PATH)

    metadata = {
        "algorithm": "TF-IDF + Logistic Regression",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "accuracy": round(float(accuracy), 4),
        "dataset_size": int(len(df)),
        "classes": sorted(y.unique().tolist()),
    }
    with open(cfg.METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved model to {cfg.MODEL_PATH}")
    print(f"Saved vectorizer to {cfg.VECTORIZER_PATH}")
    print(f"Saved metadata to {cfg.METADATA_PATH}")
    return metadata


if __name__ == "__main__":
    start = time.time()
    dataset_arg = sys.argv[1] if len(sys.argv) > 1 else None
    train(dataset_arg)
    print(f"Done in {time.time() - start:.2f}s")
