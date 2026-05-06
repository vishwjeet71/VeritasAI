# VeritasAI

**A multi-stage fact-checking pipeline built around one constraint: every verdict must be grounded in retrieved evidence, not LLM training data.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-green?style=flat-square)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-orange?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-gray?style=flat-square)](LICENSE)

https://github.com/user-attachments/assets/931de255-7161-4687-8dae-317f22b7b681

---

## The Problem

Most fact-checking tools either rely on keyword search (brittle, misses paraphrased claims) or lookup tables (can't handle new claims). Real-world misinformation is rephrased, compound, and vague. The hard problems are:

- **Claim extraction is noisy** — articles contain opinions, fragments, and navigation garbage alongside real claims.
- **Sources aren't equally credible** — returning ten links means nothing if they're all tabloids.
- **Evidence is buried** — a 2,000-word article may have two sentences relevant to your claim. Finding them matters.
- **Attribution is subtle** — "X did it" and "X and Y did it jointly" are different facts. The verdict prompt handles this explicitly: agent attribution is decomposed as its own checkable component, and a mismatch on agent alone forces a `Contradicted` verdict even if the rest of the claim holds.

VeritasAI handles all four.

---

## Pipeline

```
User Input (claim text or article URL)
        │
        ▼
┌──────────────────────┐
│  Input Classification │  urlparse → routes to URL path or query path
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    │             │
 URL path    Query path
    │             │
    ▼             ▼
trafilatura   rephrase_and_score()
fetch + spaCy  (Groq LLM — extract,
sentence       score 0–1, reject
patterns       junk, return top 5)
    │             │
    └──────┬──────┘
           ▼
    Top 5 claims → User selects
           │
           ▼
┌──────────────────────────┐
│  Search Query Generation  │  Groq generates 3 query variants per claim:
│                           │  fact_check_query / gnews_specific / gnews_broad
└──────────┬────────────────┘
           │
           ▼
┌──────────────────────────┐
│  Fact Check DB (fast path)│  Google Fact Check Tools API
│  → Semantic filter 0.80  │  cosine similarity gates irrelevant results
└──────────┬────────────────┘
           │ (miss)
           ▼
┌──────────────────────────────────────────────────┐
│  Three-tier Search Fallback                       │
│  gnews_specific → gnews_broad → Serper.dev        │
│  → Top 3 sources by 6-factor credibility score   │
└──────────┬───────────────────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│  Evidence Extraction      │  trafilatura fetches, spaCy sentences,
│                           │  all-MiniLM-L6-v2 cosine sim,
│                           │  top 2 chunks per source
└──────────┬────────────────┘
           │
           ▼
┌──────────────────────────┐
│  LLM Verdict              │  Groq Llama 3.3 70B
│                           │  Supported / Contradicted /
│                           │  Inconclusive / Unverifiable
└──────────────────────────┘
```

Batch mode (`verify_claims_batch`) parallelises the evidence + verdict stage with `ThreadPoolExecutor`, maintaining result order via index mapping.

---

## Key Design Decisions

**Why spaCy patterns before LLM scoring?**  
Running every sentence through Groq would be slow and expensive. spaCy filters to candidates that pass semantic pattern gates (entity+verb, entity+stats, event+time/place) before any LLM call. The LLM only sees ~20% of article sentences.

**Why Google Sheets as the credibility cache?**  
MBFC (Media Bias/Fact Check) has no public API. The system scrapes it on first encounter per organization and caches results in Google Sheets — zero infrastructure, free persistence, survives restarts. The in-memory dict cache sits on top for hot-path reads; Sheets is the durable layer.

**Why semantic filtering on Fact Check DB results?**  
The Google Fact Check API returns results by keyword. A query for "Chandrayaan-3 south pole" might surface tangentially related claims. A cosine similarity threshold of 0.80 gates these before they reach the verdict engine — preventing hallucinated verdicts from mismatched evidence.

**Why three search query variants?**  
Different retrieval systems need different query shapes. `fact_check_query` is natural language for fact-checker articles. `gnews_specific` is short keywords for news APIs. `gnews_broad` is a 2-4 word fallback when the specific query returns nothing. This tiered approach handles both breaking news and obscure claims.

**Why top-2 evidence chunks per source instead of full articles?**  
Sending 2,000 words to an LLM inflates tokens, dilutes focus, and increases hallucination risk. Cosine similarity against the claim picks the two most semantically relevant sentences per article. The verdict model gets signal, not noise.

**Verdict prompt engineering:**  
The verdict prompt explicitly decomposes claims into SUBJECT / ACTION / AGENT / QUANTITY / TIME / LOCATION before verdict assignment. Attribution rules are hardcoded: "A did X" vs "A and B did X" are treated as factually distinct. The model is forbidden from using training knowledge — it must ground verdicts in provided chunks only.

---

## Credibility Scoring Model

Scores are weighted across six MBFC-derived dimensions:

| Signal | Weight |
|---|---|
| Factual Reporting (int → normalized) | 37% |
| MBFC Credibility Rating | 25% |
| Bias Rating (extremity penalised) | 22% |
| Press Freedom (country-level) | 12% |
| Traffic / Popularity | 2.5% |
| Media Type | 1.5% |

Missing dimensions are excluded from the weighted average rather than defaulted to zero — a source with no traffic data isn't penalised for it.

---

## Tech Stack

| Component | Tool | Why |
|---|---|---|
| Article fetching | `trafilatura` | Best boilerplate removal; async-compatible via `asyncio.to_thread` |
| Claim extraction | `spaCy en_core_web_md` | Fast, rule-transparent NER + dependency parsing |
| Embeddings | `all-MiniLM-L6-v2` | 384-dim, fast, good semantic similarity for retrieval |
| LLM | Groq (Llama 3.3 70B) | Sub-second inference; deterministic at temp=0.1 |
| Fact Check DB | Google Fact Check Tools API | Pre-reviewed claims from professional fact-checkers |
| News search | GNews + Serper.dev | GNews is cheaper; Serper is the fallback with broader coverage |
| Credibility data | MBFC via `BeautifulSoup` | No public API exists; scraping is the only option |
| Persistent cache | `gspread` + Google Sheets | Zero infra, free, survives restarts |
| Backend | FastAPI | Async-native, low overhead |
| Frontend | Vanilla HTML/CSS/JS | No framework overhead for a single-page tool |

---

## Setup

```bash
git clone https://github.com/vishwjeet71/VeritasAI
cd VeritasAI
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_md
```

**`.env` required:**
```
GroqApi=your_groq_api_key
FactCheckDbApi=your_google_factcheck_api_key
gnewsApi=your_gnews_api_key
serperDev=your_serperdev_api_key          # optional fallback
GOOGLE_SHEETS_CREDENTIALS_PATH=path/to/service_account.json
```

**Google Sheets setup (most friction-heavy part):**  
Create a spreadsheet named `organizationsCredibility`. In Google Cloud Console, create a service account, download the JSON key, and grant it Editor access to the sheet. Enable both the Sheets API and Drive API for your project. The service account needs both scopes — missing the Drive scope causes a silent 403 on first write (this is a known gotcha). Set `GOOGLE_SHEETS_CREDENTIALS_PATH` in your `.env` to the JSON key path.

```bash
uvicorn main:app --reload
```

---

## What This Is Not

- **Not a ChatGPT wrapper with browsing.** The LLM is explicitly forbidden from using training knowledge in the verdict prompt — it can only reason over the retrieved evidence chunks provided to it. If no chunk supports a claim, the verdict is `Unverifiable`, not a confident guess.
- **Not a search summarizer.** Summarizing the top search results is exactly what existing tools already do wrong — it rewards SEO, not accuracy. VeritasAI scores sources by credibility before fetching, extracts semantically relevant sentences before passing to the LLM, and gates fact-check DB results by cosine similarity before trusting them.
- **Not production-ready.** MBFC scraping breaks on site structure changes. The GNews free tier caps out fast on batch queries. There's no verdict caching, so repeated identical claims re-run the full pipeline. These are known constraints, not oversights.

---

## Known Limitations

- **GNews API free tier** returns max 10 articles/query with a daily cap. Obscure claims will frequently hit the `Serper` fallback or fail source discovery entirely.
- **MBFC coverage is incomplete** — niche or non-English publications often return empty rows. The system defaults to 0.5 (neutral) for unknown sources rather than flagging them.
- **Evidence extraction assumes extractable HTML.** Paywalled, JavaScript-rendered, or bot-blocked pages return `None` and are silently dropped from the source pool.
- **Batch verdict parallelism (max 5 threads)** — scaling this higher risks hitting Groq rate limits on the free tier.
- **MBFC scraping is fragile** — any structural change to mediabiasfactcheck.com breaks `_extract_mbfc_data`.

---

## Future Work

- Replace the current MBFC scraping method with a more stable credibility source, such as the NewsGuard API, or improve the scraping logic so website changes do not affect the results. This will make the system more reliable and easier to maintain at scale.

- Fine-tune a lightweight classifier for claim extraction instead of relying only on spaCy heuristic rules. This can improve claim detection, reduce noise, and produce more accurate and relevant results.

- Add image and video claim verification features so the system can detect and analyze claims made through visual content. This can strengthen the verification pipeline by using visual evidence alongside text-based evidence.

- Improve the search query generation and article collection process to gather more relevant, accurate, and high-quality evidence for fact verification.

---

## Project Structure

```
VeritasAI/
├── backend/
│   ├── input_handler.py        # URL vs query classification
│   ├── article_fetcher.py      # Async article fetching (trafilatura + ThreadPoolExecutor)
│   ├── claim_extractor.py      # spaCy candidate extraction + LLM query extraction
│   ├── groq_client.py          # rephrase_and_score, generate_search_queries, generate_verdict
│   ├── search_handler.py       # GNews + Serper with credibility filtering
│   ├── credibility_scorer.py   # MBFC scraping + 6-factor scoring + Sheets cache
│   ├── fact_check_db.py        # Google Fact Check API + semantic relevance filtering
│   ├── evidence_extractor.py   # SentenceTransformer + cosine sim evidence chunking
│   ├── verification_pipeline.py# Orchestration — single claim + batch modes
│   └── prompts.py              # All LLM prompt templates
├── frontend/
│   └── index.html
│   └── styles.css
│   └── app.js
├── main.py                     # FastAPI app
└── requirements.txt
```