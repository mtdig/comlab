"""
CommLab Glossary Trainer – FastAPI backend
"""

import json
import random
import re
import time
import uvicorn
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

import duckdb
import ollama
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

#  Config 

GLOSSARY_PATH = Path(__file__).parent / "glossary.json"
DB_PATH       = Path(__file__).parent / "progress.duckdb"
STATIC_DIR    = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"
OLLAMA_MODEL  = "mistral"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

#  DB setup 

@contextmanager
def get_db():
    conn = duckdb.connect(str(DB_PATH))
    try:
        yield conn
    finally:
        conn.close()

def to_dicts(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                term       TEXT    NOT NULL,
                unit       INTEGER NOT NULL,
                mode       TEXT    NOT NULL,
                score      INTEGER NOT NULL,
                correct    INTEGER NOT NULL,
                ts         BIGINT  NOT NULL,
                time_taken INTEGER NOT NULL DEFAULT 0,
                expired    INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Migrate existing tables that lack the new columns
        existing = {r[0] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'attempts'"
        ).fetchall()}
        if 'time_taken' not in existing:
            conn.execute("ALTER TABLE attempts ADD COLUMN time_taken INTEGER DEFAULT 0")
        if 'expired' not in existing:
            conn.execute("ALTER TABLE attempts ADD COLUMN expired INTEGER DEFAULT 0")

#  Load glossary 

def load_glossary() -> list[dict]:
    with open(GLOSSARY_PATH) as f:
        return json.load(f)

GLOSSARY: list[dict] = load_glossary()

def _build_units() -> list[dict]:
    seen: dict[int, str] = {}
    for e in GLOSSARY:
        u = e["unit"]
        if u not in seen:
            seen[u] = e["unit_name"]
    return [{"unit": u, "unit_name": n} for u, n in sorted(seen.items())]

UNITS: list[dict] = _build_units()

#  Lifespan 

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

#  Grading helpers 

def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())

def find_entry(term: str, unit: int) -> dict | None:
    for e in GLOSSARY:
        if e["unit"] == unit and normalize(e["term"]) == normalize(term):
            return e
    return None

def grade_def_to_term(user_answer: str, correct_term: str) -> tuple[bool, int, str]:
    user_norm    = normalize(user_answer.strip())
    correct_norm = normalize(correct_term)
    if user_norm == correct_norm:
        return True, 100, "Perfect match!"
    words = [normalize(w) for w in correct_term.split()]
    matched = sum(1 for w in words if w in user_norm)
    if matched == len(words):
        return True, 90, "Correct! (slightly different formatting)"
    if matched >= len(words) * 0.6:
        score = int(60 * matched / len(words))
        return False, score, f"Partially correct – the answer was: {correct_term}"
    return False, 0, f"Incorrect. The correct term was: {correct_term}"

def grade_def_to_term_ollama(user_answer: str, correct_term: str, reference_def: str) -> tuple[bool, int, str]:
    """Use Ollama to leniently recheck a def→term answer."""
    prompt = f"""You are checking a vocabulary exercise for IT/English learners.

The student was shown a definition and asked to write the term.
Definition: "{reference_def}"
Expected term: "{correct_term}"
Student's answer: "{user_answer}"

Is the student's answer an acceptable way to refer to the expected term?
Be lenient with abbreviations, plural forms, and slight alternate phrasings.
A score of 70+ counts as correct.

Reply ONLY with valid JSON (no other text):
{{"score": <integer 0-100>, "correct": <true or false>, "feedback": "<one concise sentence>"}}"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        raw = response["message"]["content"].strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)
        score   = max(0, min(100, int(data["score"])))
        correct = bool(data["correct"]) or score >= 70
        return correct, score, str(data["feedback"])
    except Exception as e:
        return False, 0, f"(Ollama unavailable: {e})"

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
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)
        score    = max(0, min(100, int(data["score"])))
        correct  = bool(data["correct"]) or score >= 70
        feedback = str(data["feedback"])
        return correct, score, feedback
    except Exception as e:
        keywords = [w.lower() for w in reference_def.split() if len(w) > 4]
        matched  = sum(1 for k in keywords if k in user_answer.lower())
        ratio    = matched / max(len(keywords), 1)
        score    = int(ratio * 100)
        correct  = score >= 55
        return correct, score, f"(Ollama unavailable: {e}) Basic keyword match: {score}/100"

def _build_result(correct: bool, score: int, feedback: str, reference: str) -> dict:
    if correct:
        cls, icon, title = "correct", "✅", "Correct!"
    elif score >= 50:
        cls, icon, title = "partial", "🟡", "Partial credit"
    else:
        cls, icon, title = "wrong", "❌", "Incorrect"
    return {
        "cls": cls, "icon": icon, "title": title,
        "score": score, "correct": correct,
        "feedback": feedback, "reference": reference,
    }

def _pick_question(mode: str, unit_filter: str) -> dict:
    units = [int(u) for u in unit_filter.split(',') if u.strip()]
    pool = [e for e in GLOSSARY if e["unit"] in units] if units else GLOSSARY
    if not pool:
        raise HTTPException(404, "No entries for that unit")
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT term, unit,
                   AVG(score)      AS avg_score,
                   SUM(expired)    AS total_expired,
                   AVG(time_taken) AS avg_time
            FROM attempts WHERE mode = ? GROUP BY term, unit
            """,
            [mode],
        )
        stats = {(r["term"], r["unit"]): r for r in to_dicts(cur)}

    # Phase 1 — exhaust unseen terms before repeating anything
    unseen = [e for e in pool if (e["term"], e["unit"]) not in stats]
    if unseen:
        return random.choice(unseen)

    # Phase 2 — all seen: weight by fail ratio and avg time taken (longer = worse)
    weights = []
    for e in pool:
        st = stats[(e["term"], e["unit"])]
        score_factor   = max(0.0, (100.0 - (st["avg_score"]     or 0)) / 100.0)
        time_factor    = min((st["avg_time"]      or 0) / 60.0, 1.0)
        expired_factor = min((st["total_expired"] or 0) / 5.0,  1.0)
        weights.append(1.0 + 2.0 * score_factor + 1.0 * time_factor + 1.5 * expired_factor)
    return random.choices(pool, weights=weights, k=1)[0]

def _pool_size(unit_filter: str) -> int:
    units = [int(u) for u in unit_filter.split(',') if u.strip()]
    pool = [e for e in GLOSSARY if e["unit"] in units] if units else GLOSSARY
    return len(pool)

#  Routes 

@app.get("/")
def index(request: Request):
    entry = _pick_question("def_to_term", "")
    ctx = {
        "units":       UNITS,
        "mode":        "def_to_term",
        "term":        entry["term"],
        "unit":        entry["unit"],
        "definition":  entry["definition"],
        "unit_filter": "",
        "pool_size":   _pool_size(""),
        "answered":    False,
        "result":      None,
    }
    return templates.TemplateResponse(request, "index.html", ctx)

@app.get("/question")
def question(request: Request, mode: str = "def_to_term", unit: str = ""):
    entry = _pick_question(mode, unit)
    ctx = {
        "mode":        mode,
        "term":        entry["term"],
        "unit":        entry["unit"],
        "definition":  entry["definition"],
        "unit_filter": unit,
        "pool_size":   _pool_size(unit),
        "answered":    False,
        "result":      None,
    }
    return templates.TemplateResponse(request, "partials/question_wrap.html", ctx)

@app.post("/grade")
def grade(
    request:     Request,
    term:        str = Form(...),
    unit:        str = Form(...),
    mode:        str = Form(...),
    unit_filter: str = Form(""),
    answer:      str = Form(""),
    expired:     int = Form(0),
    time_taken:  int = Form(0),
):
    unit_int = int(unit)
    entry = find_entry(term, unit_int)
    if not entry:
        raise HTTPException(404, f"Term '{term}' not found in unit {unit_int}")

    if expired:
        correct, score, feedback = False, 0, "⏱ Time's up!"
        reference = entry["term"] if mode == "def_to_term" else entry["definition"]
    elif mode == "def_to_term":
        correct, score, feedback = grade_def_to_term(answer, entry["term"])
        reference = entry["term"]
    else:
        correct, score, feedback = grade_term_to_def_ollama(
            entry["term"], entry["definition"], answer
        )
        reference = entry["definition"]

    with get_db() as conn:
        conn.execute(
            "INSERT INTO attempts (term, unit, mode, score, correct, ts, time_taken, expired) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [entry["term"], entry["unit"], mode, score, int(correct),
             int(time.time()), max(0, time_taken), int(bool(expired))]
        )

    result = _build_result(correct, score, feedback, reference)
    result["user_answer"] = answer
    result["ai_checked"] = False
    ctx = {
        "mode":        mode,
        "term":        entry["term"],
        "unit":        entry["unit"],
        "definition":  entry["definition"],
        "unit_filter": unit_filter,
        "pool_size":   _pool_size(unit_filter),
        "answered":    True,
        "result":      result,
    }
    return templates.TemplateResponse(request, "partials/question_wrap.html", ctx)

@app.post("/recheck")
def recheck(
    request:     Request,
    term:        str = Form(...),
    unit:        str = Form(...),
    mode:        str = Form(...),
    unit_filter: str = Form(""),
    answer:      str = Form(""),
    prev_score:  int = Form(0),
):
    unit_int = int(unit)
    entry = find_entry(term, unit_int)
    if not entry:
        raise HTTPException(404, f"Term '{term}' not found in unit {unit_int}")

    correct, score, feedback = grade_def_to_term_ollama(answer, entry["term"], entry["definition"])

    # Overwrite the most recent attempt for this term/unit/mode with the AI verdict
    with get_db() as conn:
        conn.execute(
            """UPDATE attempts SET score = ?, correct = ?
               WHERE ts = (SELECT MAX(ts) FROM attempts WHERE term = ? AND unit = ? AND mode = ?)
                 AND term = ? AND unit = ? AND mode = ?""",
            [score, int(correct),
             entry["term"], entry["unit"], mode,
             entry["term"], entry["unit"], mode],
        )

    result = _build_result(correct, score, feedback, entry["term"])
    result["user_answer"] = answer
    result["ai_checked"]  = True
    result["prev_score"]  = prev_score

    ctx = {
        "mode":        mode,
        "term":        entry["term"],
        "unit":        entry["unit"],
        "definition":  entry["definition"],
        "unit_filter": unit_filter,
        "pool_size":   _pool_size(unit_filter),
        "answered":    True,
        "result":      result,
    }
    return templates.TemplateResponse(request, "partials/question_wrap.html", ctx)

@app.get("/study/cards")
def study_cards(request: Request, unit: str = "", order: str = "grouped"):
    units = [int(u) for u in unit.split(',') if u.strip()]
    pool = [e for e in GLOSSARY if e["unit"] in units] if units else GLOSSARY
    terms = list(pool)
    if order == "mixed":
        random.shuffle(terms)
    return templates.TemplateResponse(request, "partials/study_cards.html", {
        "terms": terms,
    })

#  JSON API routes 

@app.get("/api/units")
def api_units():
    return UNITS

@app.get("/api/stats")
def api_stats(unit: int = 0):
    with get_db() as conn:
        if unit == 0:
            cur = conn.execute(
                "SELECT mode, COUNT(*) AS total, SUM(correct) AS hits, AVG(score) AS avg_score "
                "FROM attempts GROUP BY mode"
            )
        else:
            cur = conn.execute(
                "SELECT mode, COUNT(*) AS total, SUM(correct) AS hits, AVG(score) AS avg_score "
                "FROM attempts WHERE unit=? GROUP BY mode",
                [unit]
            )
        return to_dicts(cur)

@app.get("/api/weak_spots")
def api_weak_spots(limit: int = 10):
    with get_db() as conn:
        cur = conn.execute("""
            SELECT term, unit, mode,
                   COUNT(*) AS attempts,
                   SUM(correct) AS correct_count,
                   AVG(score) AS avg_score
            FROM attempts
            GROUP BY term, unit, mode
            HAVING COUNT(*) >= 2
            ORDER BY avg_score ASC
            LIMIT ?
        """, [limit])
        return to_dicts(cur)

@app.post("/api/reset")
def api_reset():
    with get_db() as conn:
        conn.execute("DELETE FROM attempts")
    return {"ok": True}

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
