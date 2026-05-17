import json
import re

import ollama

from app.config import OLLAMA_MODEL
from app.utils import normalize


def grade_def_to_term(user_answer: str, correct_term: str) -> tuple[bool, int, str]:
    user_norm    = normalize(user_answer.strip())
    correct_norm = normalize(correct_term)
    if user_norm == correct_norm:
        return True, 100, "Perfect match!"
    words   = [normalize(w) for w in correct_term.split()]
    matched = sum(1 for w in words if w in user_norm)
    if matched == len(words):
        return True, 90, "Correct! (slightly different formatting)"
    if matched >= len(words) * 0.6:
        score = int(60 * matched / len(words))
        return False, score, f"Partially correct – the answer was: {correct_term}"
    return False, 0, f"Incorrect. The correct term was: {correct_term}"


def grade_def_to_term_ollama(
    user_answer: str, correct_term: str, reference_def: str
) -> tuple[bool, int, str]:
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
        raw     = response["message"]["content"].strip()
        raw     = re.sub(r"^```[a-z]*\n?", "", raw)
        raw     = re.sub(r"\n?```$", "", raw)
        data    = json.loads(raw)
        score   = max(0, min(100, int(data["score"])))
        correct = bool(data["correct"]) or score >= 70
        return correct, score, str(data["feedback"])
    except Exception as e:
        return False, 0, f"(Ollama unavailable: {e})"


def grade_term_to_def_ollama(
    term: str, reference_def: str, user_answer: str
) -> tuple[bool, int, str]:
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
        raw      = response["message"]["content"].strip()
        raw      = re.sub(r"^```[a-z]*\n?", "", raw)
        raw      = re.sub(r"\n?```$", "", raw)
        data     = json.loads(raw)
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


def build_result(correct: bool, score: int, feedback: str, reference: str) -> dict:
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
