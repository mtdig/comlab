import random

from fastapi import APIRouter, Request

from app.glossary import GLOSSARY, filter_pool
from app.templates import templates

router = APIRouter()


@router.get("/study/cards")
def study_cards(request: Request, unit: str = "", order: str = "grouped"):
    terms = filter_pool(GLOSSARY, unit)
    if order == "mixed":
        terms = list(terms)
        random.shuffle(terms)
    return templates.TemplateResponse(request, "partials/study_cards.html", {"terms": terms})
