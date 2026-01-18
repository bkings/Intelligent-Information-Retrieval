import re
import json
import numpy as np

from typing import List, Dict, Any
from constants.constants import INDEX_FILE_PATH
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def preprocess(text: str) -> str:
    """Tokenize, lowercase, remove punctuations"""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(text.split())  # Normalizing the whitespaces


def load_index() -> List[Dict[str, Any]]:
    """Load crawled data"""
    if not INDEX_FILE_PATH.exists():
        return []
    with open(INDEX_FILE_PATH) as f:
        return json.load(f)


def build_tfidf_index(docs: List[Dict[str, Any]]) -> Dict:
    contents = [pub.get("content", "") for pub in docs]
    vectorizer = TfidfVectorizer(
        stop_words="english", min_df=1, max_df=0.9, ngram_range=(1, 2)
    )
    tfidf_matrix = vectorizer.fit_transform(contents)
    return {
        "docs": docs,
        "tfidf_matrix": tfidf_matrix,
        "vectorizer": vectorizer,
        "feature_names": vectorizer.get_feature_names_out(),
    }


def search(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    docs = load_index()
    if not docs:
        return []
    index = build_tfidf_index(docs)
    query_vec = index["vectorizer"].transform([preprocess(query)])
    cosine_similarities = cosine_similarity(query_vec, index["tfidf_matrix"]).flatten()
    ranked_indices = np.argsort(cosine_similarities)[::-1][:top_k]
    results = []
    for idx in ranked_indices:
        score = cosine_similarities[idx]
        if score > 0.05:
            doc = index["docs"][idx]
            # Highlight matching parts
            snippet = doc.get("abstract", doc["title"])[:200] + "..."
            results.append({**doc, "relevancy_score": float(score), "snippet": snippet})
    return results
