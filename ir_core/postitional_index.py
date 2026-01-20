import json

from typing import List, Dict
from collections import defaultdict

from ir_core.preprocessors.preprocess import preprocess
from constants.constants import INDEX_FILE_POSITIONAL


def build_positional_index(docs: List[Dict]) -> Dict:
    """
    Tokenize each word, record positions.
    """
    postings: Dict[str, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))

    for doc_id, doc in enumerate(docs):
        tokens = preprocess(doc.get("content", doc["title"])).split()
        for pos, token in enumerate(tokens):
            postings[token][doc_id].append(pos)

    with open(INDEX_FILE_POSITIONAL, "w") as f:
        json.dump({term: dict(postings[term]) for term in postings}, f)


def load_positional_index() -> Dict:
    if INDEX_FILE_POSITIONAL.exists():
        with open(INDEX_FILE_POSITIONAL) as f:
            return json.load(f)
    return {}


def intersect_postings(post1: List[int], post2: List[int]) -> List[int]:
    """Intersect sorted doc lists"""
    i, j, common = 0, 0, []
    while i < len(post1) and j < len(post2):
        if post1[i] == post2[i]:
            common.append(post1[i])
            i += 1
            j += 1
        elif post1[i] < post2[j]:
            i += 1
        else:
            j += 1
    return common


def phrase_search(
    postings: Dict, phrase: str, docs: List[Dict], top_k: int = 10, window: int = 5
) -> List[Dict]:
    tokens = phrase.split()
    if len(tokens) == 0:
        return []

    # Get candidate docs: intersect all term postings
    candidate_docs = list(postings.get(tokens[0], {}).keys())
    for token in tokens[1:]:
        next_docs = list(postings.get(token, {}).keys())
        candidate_docs = sorted(set(candidate_docs) & set(next_docs))

    scored_results = []
    for doc_id in candidate_docs:
        doc_post_lists = [
            postings[token][doc_id] for token in tokens if doc_id in postings[token]
        ]
        if len(doc_post_lists) != len(tokens):
            continue

        # Check phrase proximity for each occurrence
        matches = 0
        for start_pos in doc_post_lists[0]:  # Anchor to first term
            positions_match = True
            for i in range(1, len(tokens)):
                expected_pos = start_pos + i  # Exact phrase len
                if expected_pos not in doc_post_lists[i]:
                    positions_match = False
                    break
            if positions_match:
                matches += 1

        if matches > 0:
            score = matches / len(tokens)  # Normalized freq
            scored_results.append((score, doc_id))

    # Rank & return
    scored_results.sort(reverse=True)
    results = []
    for score, doc_id in scored_results[:top_k]:
        doc = docs[int(doc_id)]
        results.append(
            {
                **doc,
                "relevancy_score": float(score),
                "phrase_matches": int(score * len(tokens)),
            }
        )
    return results


def keyword_search(
    postings: Dict, query: str, docs: List[Dict], top_k: int = 10
) -> List[Dict]:
    """Fallback: union + TF"""
    print("Fallback search: Keyword Search")
    tokens = set(query.split())
    doc_scores = defaultdict(float)

    for token in tokens:
        for doc_id, positions in postings.get(token, {}).items():
            tf = len(positions)
            doc_scores[doc_id] += tf

    scored = sorted(
        [(score / max(1, len(tokens)), doc_id) for doc_id, score in doc_scores.items()],
        reverse=True,
    )
    results = []
    for score, doc_id in scored[:top_k]:
        results.append({**docs[int(doc_id)], "relevancy_score": float(score)})
    return results
