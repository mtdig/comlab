from fastapi import APIRouter, Form, HTTPException, Request

from app.database import get_db
from app.glossary import GLOSSARY, UNITS, find_entry, filter_pool, pool_size
from app.grading import (
    build_result,
    grade_def_to_term,
    grade_def_to_term_ollama,
    grade_term_to_def_ollama,
)
from app.repository import insert_attempt, update_attempt_score
from app.selector import pick_question
from app.templates import templates

router = APIRouter()


@router.get("/")
def index(request: Request):
    entry = pick_question("def_to_term", "")
    ctx = {
        "units":       UNITS,
        "mode":        "def_to_term",
        "term":        entry["term"],
        "unit":        entry["unit"],
        "definition":  entry["definition"],
        "unit_filter": "",
        "pool_size":   pool_size(GLOSSARY, ""),
        "answered":    False,
        "result":      None,
    }
    return templates.TemplateResponse(request, "index.html", ctx)


@router.get("/question")
def question(request: Request, mode: str = "def_to_term", unit: str = ""):
    entry = pick_question(mode, unit)
    ctx = {
        "mode":        mode,
        "term":        entry["term"],
        "unit":        entry["unit"],
        "definition":  entry["definition"],
        "unit_filter": unit,
        "pool_size":   pool_size(GLOSSARY, unit),
        "answered":    False,
        "result":      None,
    }
    return templates.TemplateResponse(request, "partials/question_wrap.html", ctx)


@router.post("/grade")
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
    entry = find_entry(GLOSSARY, term, unit_int)
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
        insert_attempt(
            conn,
            term=entry["term"],
            unit=entry["unit"],
            mode=mode,
            score=score,
            correct=correct,
            time_taken=time_taken,
            expired=bool(expired),
        )

    result = build_result(correct, score, feedback, reference)
    result["user_answer"] = answer
    result["ai_checked"]  = False
    ctx = {
        "mode":        mode,
        "term":        entry["term"],
        "unit":        entry["unit"],
        "definition":  entry["definition"],
        "unit_filter": unit_filter,
        "pool_size":   pool_size(GLOSSARY, unit_filter),
        "answered":    True,
        "result":      result,
    }
    return templates.TemplateResponse(request, "partials/question_wrap.html", ctx)


@router.post("/recheck")
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
    entry = find_entry(GLOSSARY, term, unit_int)
    if not entry:
        raise HTTPException(404, f"Term '{term}' not found in unit {unit_int}")

    correct, score, feedback = grade_def_to_term_ollama(
        answer, entry["term"], entry["definition"]
    )

    with get_db() as conn:
        update_attempt_score(
            conn,
            term=entry["term"],
            unit=entry["unit"],
            mode=mode,
            score=score,
            correct=correct,
        )

    result = build_result(correct, score, feedback, entry["term"])
    result["user_answer"] = answer
    result["ai_checked"]  = True
    result["prev_score"]  = prev_score
    ctx = {
        "mode":        mode,
        "term":        entry["term"],
        "unit":        entry["unit"],
        "definition":  entry["definition"],
        "unit_filter": unit_filter,
        "pool_size":   pool_size(GLOSSARY, unit_filter),
        "answered":    True,
        "result":      result,
    }
    return templates.TemplateResponse(request, "partials/question_wrap.html", ctx)
