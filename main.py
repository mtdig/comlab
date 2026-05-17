"""
CommLab Glossary Trainer – FastAPI backend
Requires: pip install fastapi uvicorn ollama
"""

import json
import random
import re
import sqlite3
import time
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path

import ollama
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─── Config ──────────────────────────────────────────────────────────────────

GLOSSARY_PATH = Path(__file__).parent / "glossary.json"
DB_PATH       = Path(__file__).parent / "progress.db"
STATIC_DIR    = Path(__file__).parent / "static"
OLLAMA_MODEL  = "mistral"   # change to phi3:mini, llama3.2:3b, etc.

# ─── DB setup ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                term      TEXT    NOT NULL,
                unit      INTEGER NOT NULL,
                mode      TEXT    NOT NULL,   -- 'term_to_def' or 'def_to_term'
                score     INTEGER NOT NULL,   -- 0-100
                correct   INTEGER NOT NULL,   -- 1/0
                ts        INTEGER NOT NULL
            )
        """)
        conn.commit()

# ─── Load glossary ───────────────────────────────────────────────────────────

def load_glossary():
    with open(GLOSSARY_PATH) as f:
        return json.load(f)

GLOSSARY = load_glossary()

# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="CommLab Glossary Trainer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ──────────────────────────────────────────────────────────────────

class GradeRequest(BaseModel):
    term: str
    unit: int
    mode: str           # 'term_to_def' | 'def_to_term'
    user_answer: str

class GradeResponse(BaseModel):
    correct: bool
    score: int          # 0-100
    feedback: str
    reference: str      # the correct answer for display

# ─── Helpers ─────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())

def find_entry(term: str, unit: int) -> dict | None:
    for e in GLOSSARY:
        if e["unit"] == unit and normalize(e["term"]) == normalize(term):
            return e
    return None

def grade_def_to_term(user_answer: str, correct_term: str) -> tuple[bool, int, str]:
    """Simple fuzzy match for mode def_to_term (definition given, guess the word)."""
    user_norm    = normalize(user_answer.strip())
    correct_norm = normalize(correct_term)
    if user_norm == correct_norm:
        return True, 100, "Perfect match!"
    # Allow partial credit for long compound terms
    words = [normalize(w) for w in correct_term.split()]
    matched = sum(1 for w in words if w in user_norm)
    if matched == len(words):
        return True, 90, "Correct! (slightly different formatting)"
    if matched >= len(words) * 0.6:
        score = int(60 * matched / len(words))
        return False, score, f"Partially correct – the answer was: {correct_term}"
    return False, 0, f"Incorrect. The correct term was: {correct_term}"

def grade_term_to_def_ollama(term: str, reference_def: str, user_answer: str) -> tuple[bool, int, str]:
    """Use Ollama to grade a free-text definition answer."""
    prompt = f"""You are grading a vocabulary exercise for English learners studying IT terminology.

Term: "{term}"
Reference definition: "{reference_def}"
Student's explanation: "{user_answer}"

Does the student's explanation correctly capture the core meaning of the term?
Be lenient with phrasing – reward understanding over word-for-word accuracy.
A score of 70+ means the student understands the concept.

Reply ONLY with valid JSON in this exact format (no other text):
{{"score": <integer 0-100>, "correct": <true or false>, "feedback": "<one concise sentence>"}}"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        raw = response["message"]["content"].strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)
        score   = max(0, min(100, int(data["score"])))
        correct = bool(data["correct"]) or score >= 70
        feedback = str(data["feedback"])
        return correct, score, feedback
    except Exception as e:
        # Fallback: basic keyword check
        keywords = [w.lower() for w in reference_def.split() if len(w) > 4]
        matched  = sum(1 for k in keywords if k in user_answer.lower())
        ratio    = matched / max(len(keywords), 1)
        score    = int(ratio * 100)
        correct  = score >= 55
        return correct, score, f"(Ollama unavailable: {e}) Basic keyword match: {score}/100"

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/api/units")
def get_units():
    seen = {}
    for e in GLOSSARY:
        u = e["unit"]
        if u not in seen:
            seen[u] = e["unit_name"]
    return [{"unit": u, "name": n} for u, n in sorted(seen.items())]

@app.get("/api/glossary")
def get_glossary(unit: int = 0):
    pool = GLOSSARY if unit == 0 else [e for e in GLOSSARY if e["unit"] == unit]
    return pool

@app.get("/api/question")
def get_question(mode: str = "def_to_term", unit: int = 0):
    """
    mode: 'def_to_term' – show definition, student types the term
          'term_to_def' – show term, student types a definition
    unit: 0 = all units
    """
    pool = GLOSSARY if unit == 0 else [e for e in GLOSSARY if e["unit"] == unit]
    if not pool:
        raise HTTPException(404, "No entries for that unit")
    entry = random.choice(pool)
    if mode == "def_to_term":
        return {
            "mode": mode,
            "unit": entry["unit"],
            "unit_name": entry["unit_name"],
            "term": entry["term"],
            "prompt": entry["definition"],
            "hint": f"Unit {entry['unit']}: {entry['unit_name']}",
        }
    else:  # term_to_def
        return {
            "mode": mode,
            "unit": entry["unit"],
            "unit_name": entry["unit_name"],
            "term": entry["term"],
            "prompt": entry["term"],
            "hint": f"Unit {entry['unit']}: {entry['unit_name']}",
        }

@app.post("/api/grade", response_model=GradeResponse)
def grade_answer(req: GradeRequest):
    entry = find_entry(req.term, req.unit)
    if not entry:
        raise HTTPException(404, f"Term '{req.term}' not found in unit {req.unit}")

    if req.mode == "def_to_term":
        correct, score, feedback = grade_def_to_term(req.user_answer, entry["term"])
        reference = entry["term"]
    else:
        correct, score, feedback = grade_term_to_def_ollama(
            entry["term"], entry["definition"], req.user_answer
        )
        reference = entry["definition"]

    # Log to DB
    with get_db() as conn:
        conn.execute(
            "INSERT INTO attempts (term, unit, mode, score, correct, ts) VALUES (?,?,?,?,?,?)",
            (entry["term"], entry["unit"], req.mode, score, int(correct), int(time.time()))
        )
        conn.commit()

    return GradeResponse(correct=correct, score=score, feedback=feedback, reference=reference)

@app.get("/api/stats")
def get_stats(unit: int = 0):
    with get_db() as conn:
        if unit == 0:
            rows = conn.execute(
                "SELECT mode, COUNT(*) as total, SUM(correct) as hits, AVG(score) as avg_score FROM attempts GROUP BY mode"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT mode, COUNT(*) as total, SUM(correct) as hits, AVG(score) as avg_score FROM attempts WHERE unit=? GROUP BY mode",
                (unit,)
            ).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/weak_spots")
def get_weak_spots(limit: int = 10):
    """Return the terms the student gets wrong most often."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT term, unit, mode,
                   COUNT(*) as attempts,
                   SUM(correct) as correct_count,
                   AVG(score) as avg_score
            FROM attempts
            GROUP BY term, unit, mode
            HAVING attempts >= 2
            ORDER BY avg_score ASC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
