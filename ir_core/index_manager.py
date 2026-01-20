import json
import numpy as np

from typing import List, Dict, Any, Tuple
from constants.constants import INDEX_FILE_PATH, INDEX_FILE_POSITIONAL
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from ir_core.postitional_index import (
    load_positional_index,
    build_positional_index,
    phrase_search,
    keyword_search,
)
from ir_core.preprocessors.preprocess import preprocess


def load_index() -> List[Dict[str, Any]]:
    """Load crawled data"""
    if not INDEX_FILE_PATH.exists():
        return []
    with open(INDEX_FILE_PATH) as f:
        return json.load(f)


def build_tfidf_index(docs: List[Dict[str, Any]]) -> Dict:
    contents = [preprocess(pub.get("content", "")) for pub in docs]
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(contents)
    return {
        "docs": docs,
        "tfidf_matrix": tfidf_matrix,
        "vectorizer": vectorizer,
        "feature_names": vectorizer.get_feature_names_out(),
    }


def search_TFIDF(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
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


def search(query: str, top_k: int = 10) -> Tuple[str, List[Dict[str, Any]]]:
    docs = load_index()
    if not docs:
        return []

    if not INDEX_FILE_POSITIONAL.exists():
        build_positional_index(docs)

    postings = load_positional_index()

    query = preprocess(query)
    # Phrase if quoted or multi-word
    if '"' in query or len(query.split()) >= 2:
        phrase = query.strip('"')
        results = phrase_search(postings, phrase, docs, top_k)
        if results:
            return "PI", results
    # Keyword fallback
    # return keyword_search(postings, query, docs, top_k)
    return "TFIDF", search_TFIDF(query, top_k)
