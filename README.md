# Vertical Search Engine

Vertical search engine for Coventry University PurePortal (`pureportal.coventry.ac.uk/en/persons`). Crawls academic profiles, indexes publications with **positional inverted index**, and provides **TF-IDF ranked search** via Streamlit UI.

## 📋 Features
- ✅ PurePortal crawler (Selenium + pagination)
- ✅ Publication extraction (titles, abstracts, fingerprints)
- ✅ Positional inverted index (term → doc → positions)
- ✅ TF-IDF ranking with proximity scoring
- ✅ Query term highlighting in results
- ✅ Google Scholar-style Streamlit interface


## 🛠️ Quick Start
```bash
# Clone & install
git clone https://github.com/bkings/Intelligent-Information-Retrieval.git
cd intelligent-information-retrieval
pip install -r requirements.txt

# Launch UI
streamlit run app.py
```


