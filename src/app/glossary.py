import json

from app.config import GLOSSARY_PATH
from app.utils import normalize


def load_glossary() -> list[dict]:
    with open(GLOSSARY_PATH) as f:
        return json.load(f)


def build_units(glossary: list[dict]) -> list[dict]:
    seen: dict[int, str] = {}
    for e in glossary:
        u = e["unit"]
        if u not in seen:
            seen[u] = e["unit_name"]
    return [{"unit": u, "unit_name": n} for u, n in sorted(seen.items())]


def find_entry(glossary: list[dict], term: str, unit: int) -> dict | None:
    for e in glossary:
        if e["unit"] == unit and normalize(e["term"]) == normalize(term):
            return e
    return None


def filter_pool(glossary: list[dict], unit_filter: str) -> list[dict]:
    units = [int(u) for u in unit_filter.split(",") if u.strip()]
    return [e for e in glossary if e["unit"] in units] if units else list(glossary)


def pool_size(glossary: list[dict], unit_filter: str) -> int:
    return len(filter_pool(glossary, unit_filter))


GLOSSARY: list[dict] = load_glossary()
UNITS: list[dict] = build_units(GLOSSARY)
