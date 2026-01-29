import re
from typing import List
from datetime import datetime


def extract_year(value):
    if value is None:
        return "N/A"

    # Ensure string
    value = str(value)

    # Try full date parsing (most reliable)
    date_formats = ["%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y"]

    for fmt in date_formats:
        try:
            return datetime.strptime(value, fmt).year
        except ValueError:
            pass

    # Fallback: extract 4-digit year via regex
    match = re.search(r"\b(19|20)\d{2}\b", value)
    if match:
        return int(match.group())

    # Nothing usable found
    return None


def highlight_terms(text: str, query_terms: List[str], color: str = "#ffeb3b") -> str:
    """Wrap query terms in <mark> tags for highlighting."""
    highlighted = text
    for term in query_terms:
        # Case-insensitive, whole-word match
        pattern = rf"\b{re.escape(term)}\b"
        highlighted = re.sub(
            pattern,
            f'<mark style="background-color: {color}; padding: 2px; border-radius: 3px;">{term}</mark>',
            highlighted,
            flags=re.IGNORECASE,
        )
    return highlighted
