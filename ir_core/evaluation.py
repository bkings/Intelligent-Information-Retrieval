from typing import List, Set, Dict
from sklearn.metrics import precision_recall_fscore_support
from constants.constants import STANDARD_MAPPING_FILE

import numpy as np
import json


def top_docs_as_standard(
    query: str,
    docs_title_flattened: List[Dict],
    results_title_flattened: List[Dict],
    k: int = 5,
) -> Set[int]:
    top_docs = []
    """Load from json first and if not present fallback to top results"""
    if STANDARD_MAPPING_FILE.exists():
        with open(STANDARD_MAPPING_FILE) as f:
            standard_data = json.load(f)
            top_docs = set(standard_data.get(query.lower(), []))
            if top_docs:
                return top_docs

    top_docs = {docs_title_flattened.index(r) for r in results_title_flattened[:k]}
    return top_docs


def evaluate_search(
    query: str, retrieved_docs: List[Dict], all_docs: List[Dict]
) -> Dict:
    docs_title_flattened = [d["title"] for d in all_docs]
    results_title_flattened = [r["title"] for r in retrieved_docs]
    standard = top_docs_as_standard(
        query, docs_title_flattened, results_title_flattened
    )

    y_true = np.zeros(len(results_title_flattened))
    y_pred = np.zeros(len(results_title_flattened))

    retrieved_ids = []
    for i, doc in enumerate(results_title_flattened):
        doc_id = docs_title_flattened.index(doc)
        retrieved_ids.append(doc_id)
        if doc_id in standard:
            y_true[i] = 1
            y_pred[i] = 1

    tp = len(standard & set(retrieved_ids))
    fp = len(set(retrieved_ids) - standard)
    fn = len(standard - set(retrieved_ids))
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )
    accuracy = tp / len(standard) if standard else 0
    return {
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "f1": round(f1, 2),
        "accuracy": round(accuracy, 2),
        "relevant_found": tp,
        "total_relevant": len(standard),
    }
