import random

from fastapi import HTTPException

from app.database import get_db
from app.glossary import GLOSSARY, filter_pool
from app.repository import get_attempt_stats
from app.schemas import AttemptStats


def _select_from_pool(pool: list[dict], stats: dict[tuple[str, int], AttemptStats]) -> dict:
    """Pure selection logic: phase-1 unseen first, phase-2 weighted by performance."""
    unseen = [e for e in pool if (e["term"], e["unit"]) not in stats]
    if unseen:
        return random.choice(unseen)
    weights = []
    for e in pool:
        st             = stats[(e["term"], e["unit"])]
        score_factor   = max(0.0, (100.0 - st.avg_score) / 100.0)
        time_factor    = min(st.avg_time / 60.0, 1.0)
        expired_factor = min(st.total_expired / 5.0, 1.0)
        weights.append(1.0 + 2.0 * score_factor + 1.0 * time_factor + 1.5 * expired_factor)
    return random.choices(pool, weights=weights, k=1)[0]


def pick_question(mode: str, unit_filter: str) -> dict:
    pool = filter_pool(GLOSSARY, unit_filter)
    if not pool:
        raise HTTPException(404, "No entries for that unit")
    with get_db() as conn:
        stats = get_attempt_stats(conn, mode)
    return _select_from_pool(pool, stats)
