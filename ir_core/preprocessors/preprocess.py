import re
import nltk
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

nltk.download("stopwords", quiet=True)
STOP_WORDS = set(stopwords.words("english"))
stemmer = PorterStemmer()


def preprocess(text: str) -> str:
    """Tokenize, lowercase, remove punctuations"""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = text.split()
    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]
    tokens = [stemmer.stem(t) for t in tokens]
    return " ".join(tokens)  # Normalizing the whitespaces

def preprocess_basic(text: str) -> str:
    """Tokenize, lowercase, remove punctuations"""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = text.split()
    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]
    return " ".join(tokens)  # Normalizing the whitespaces
