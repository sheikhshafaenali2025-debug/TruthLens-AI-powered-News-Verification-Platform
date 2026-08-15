"""
ml/predict.py

Thin command-line entry point for one-off predictions, useful for debugging
the model outside of Flask:

    python ml/predict.py "Some news article text..."

The actual Flask-facing prediction logic (with the singleton-loaded model)
lives in services/predictor.py -- this script simply calls into it.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.predictor import Predictor  # noqa: E402
from config import Config  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python ml/predict.py "News article text here"')
        sys.exit(1)

    text = sys.argv[1]
    predictor = Predictor(Config())
    result = predictor.predict(text)
    print(result)


if __name__ == "__main__":
    main()
