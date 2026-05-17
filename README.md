# CommLab Glossary Trainer

Vocabulary exercise app for the CommLab English glossary (12 units, ~300 terms).

## Features

- **Mode 1 – Definition → Word**: Given the definition, type the correct term  
  (graded with exact/fuzzy string matching — instant)

- **Mode 2 – Word → Define it**: Given the term, explain it in your own words  
  (graded by a local LLM via Ollama — lenient, rewards understanding)

- Filter by unit (or train all units at once)
- Session stats (answered / correct / avg score)
- All progress logged to SQLite (`progress.db`)
- `/api/weak_spots` endpoint shows your most missed terms

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Make sure Ollama is running and has a model pulled

```bash
ollama serve          # if not already running as a service
ollama pull mistral   # ~4 GB, good balance of speed and quality
# Alternatives for your RTX 2080 Super (8 GB VRAM):
# ollama pull phi3:mini     # ~2 GB, very fast
# ollama pull llama3.2:3b   # ~2 GB, fast
# ollama pull llama3.1:8b   # ~5 GB, most capable
```

### 3. (Optional) Change the model in main.py

```python
OLLAMA_MODEL = "mistral"   # line ~20 of main.py
```

### 4. Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open in browser

```
http://localhost:8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/units` | List all units |
| GET | `/api/question?mode=&unit=` | Get a random question |
| POST | `/api/grade` | Grade a submitted answer |
| GET | `/api/stats?unit=` | Session statistics |
| GET | `/api/weak_spots?limit=` | Your weakest terms |

## Grading details

**def_to_term mode**: Simple normalized string comparison. Handles minor typos
via word-level partial matching for multi-word terms.

**term_to_def mode**: Ollama receives the term, the reference definition, and
your answer, and returns a score (0–100) + one-sentence feedback. The model is
prompted to reward conceptual understanding over verbatim wording. Score ≥ 70
counts as correct.

If Ollama is unavailable, a basic keyword-overlap fallback is used.

## Project structure

```
glossary_trainer/
├ main.py           # FastAPI backend
├ glossary.json     # All 300+ terms extracted from the PDF
├ requirements.txt
├ progress.db       # Created on first run (SQLite)
└ static/
    └ index.html    # Single-file frontend
```
