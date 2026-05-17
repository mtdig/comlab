from fastapi import APIRouter

from app.database import get_db
from app.glossary import UNITS
from app.repository import get_stats_by_mode, get_weak_spots, reset_attempts

router = APIRouter(prefix="/api")


@router.get("/units")
def api_units():
    return UNITS


@router.get("/stats")
def api_stats(unit: int = 0):
    with get_db() as conn:
        return get_stats_by_mode(conn, unit)


@router.get("/weak_spots")
def api_weak_spots(limit: int = 10):
    with get_db() as conn:
        return get_weak_spots(conn, limit)


@router.post("/reset")
def api_reset():
    with get_db() as conn:
        reset_attempts(conn)
    return {"ok": True}
