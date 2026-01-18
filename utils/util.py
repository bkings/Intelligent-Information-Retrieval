import re
from datetime import datetime

def extract_year(value):
    if value is None:
        return "N/A"

    # Ensure string
    value = str(value)

    #Try full date parsing (most reliable)
    date_formats = [
        "%d %b %Y",
        "%d %B %Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y"
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(value, fmt).year
        except ValueError:
            pass

    #Fallback: extract 4-digit year via regex
    match = re.search(r"\b(19|20)\d{2}\b", value)
    if match:
        return int(match.group())

    #Nothing usable found
    return None
