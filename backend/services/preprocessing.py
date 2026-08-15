"""
services/preprocessing.py

Shared text-cleaning pipeline used identically by training (ml/train_model.py)
and inference (services/predictor.py). Keeping this logic in one place
guarantees the model always sees text in the same shape it was trained on.
"""

import re
import string
from functools import lru_cache
from typing import List

# Built-in fallback stopword list. Used whenever NLTK (or its downloaded
# corpora) is unavailable -- e.g. on a machine with restricted network
# access -- so preprocessing never hard-crashes the app on startup.
_FALLBACK_STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "you're",
    "you've", "you'll", "you'd", "your", "yours", "yourself", "yourselves", "he",
    "him", "his", "himself", "she", "she's", "her", "hers", "herself", "it", "it's",
    "its", "itself", "they", "them", "their", "theirs", "themselves", "what",
    "which", "who", "whom", "this", "that", "that'll", "these", "those", "am",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if",
    "or", "because", "as", "until", "while", "of", "at", "by", "for", "with",
    "about", "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "s", "t", "can", "will", "just", "don", "don't", "should", "now",
}

_LEMMATIZER = None
_STOPWORDS = _FALLBACK_STOPWORDS

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer

    def _ensure_nltk_data() -> None:
        """Download required NLTK corpora on first run (no-op if already present)."""
        required = [
            ("corpora/stopwords", "stopwords"),
            ("corpora/wordnet", "wordnet"),
            ("corpora/omw-1.4", "omw-1.4"),
        ]
        for path, package in required:
            try:
                nltk.data.find(path)
            except LookupError:
                nltk.download(package, quiet=True)

    _ensure_nltk_data()
    _STOPWORDS = set(stopwords.words("english"))
    _LEMMATIZER = WordNetLemmatizer()
    # Sanity-check the lemmatizer actually has wordnet data behind it.
    _LEMMATIZER.lemmatize("test")
except Exception:
    # NLTK not installed, or its corpora couldn't be downloaded (no network
    # access, offline environment, etc). Fall back to the built-in stopword
    # list and a no-op lemmatizer so preprocessing -- and the app -- keeps working.
    _LEMMATIZER = None
    _STOPWORDS = _FALLBACK_STOPWORDS

_URL_PATTERN = re.compile(r"http\S+|www\.\S+")
_HTML_PATTERN = re.compile(r"<.*?>")
_NUMBER_PATTERN = re.compile(r"\d+")
_MULTISPACE_PATTERN = re.compile(r"\s+")
_PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation)


def to_lowercase(text: str) -> str:
    """Lowercase all characters."""
    return text.lower()


def remove_urls(text: str) -> str:
    """Strip http(s):// and www. links."""
    return _URL_PATTERN.sub(" ", text)


def remove_html_tags(text: str) -> str:
    """Strip any HTML/XML tags."""
    return _HTML_PATTERN.sub(" ", text)


_NON_WORD_PATTERN = re.compile(r"[^\w\s]", flags=re.UNICODE)


def remove_punctuation(text: str) -> str:
    """Remove ASCII punctuation plus any remaining non-word symbols (e.g. em dashes, curly quotes)."""
    text = text.translate(_PUNCTUATION_TABLE)
    return _NON_WORD_PATTERN.sub(" ", text)


def remove_numbers(text: str) -> str:
    """Remove standalone digit sequences."""
    return _NUMBER_PATTERN.sub(" ", text)


def remove_extra_spaces(text: str) -> str:
    """Collapse repeated whitespace and trim ends."""
    return _MULTISPACE_PATTERN.sub(" ", text).strip()


def remove_stopwords(tokens: List[str]) -> List[str]:
    """Filter out common English stopwords."""
    return [t for t in tokens if t not in _STOPWORDS]


def lemmatize_tokens(tokens: List[str]) -> List[str]:
    """Reduce each token to its base/dictionary form (falls back to a no-op if
    NLTK's WordNet data isn't available in this environment)."""
    if _LEMMATIZER is None:
        return tokens
    return [_LEMMATIZER.lemmatize(t) for t in tokens]


@lru_cache(maxsize=4096)
def clean_text(text: str) -> str:
    """
    Full preprocessing pipeline applied identically at train and predict time.

    Order: lowercase -> strip URLs -> strip HTML -> strip punctuation ->
    strip numbers -> collapse whitespace -> tokenize -> drop stopwords ->
    lemmatize -> rejoin.

    Cached with lru_cache since the same article text is often re-analyzed
    (e.g. retries) within a short window.
    """
    if not text:
        return ""

    cleaned = to_lowercase(text)
    cleaned = remove_urls(cleaned)
    cleaned = remove_html_tags(cleaned)
    cleaned = remove_punctuation(cleaned)
    cleaned = remove_numbers(cleaned)
    cleaned = remove_extra_spaces(cleaned)

    tokens = cleaned.split()
    tokens = remove_stopwords(tokens)
    tokens = lemmatize_tokens(tokens)

    return " ".join(tokens)
