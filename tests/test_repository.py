import duckdb
import pytest

from app.database import init_schema
from app.repository import (
    get_attempt_stats,
    get_stats_by_mode,
    get_weak_spots,
    insert_attempt,
    reset_attempts,
    update_attempt_score,
)


@pytest.fixture
def db():
    conn = duckdb.connect(":memory:")
    init_schema(conn)
    yield conn
    conn.close()


def _insert(db, term="TCP", unit=1, mode="def_to_term", score=100, correct=True,
            time_taken=5, expired=False):
    insert_attempt(db, term=term, unit=unit, mode=mode, score=score,
                   correct=correct, time_taken=time_taken, expired=expired)


def test_insert_and_get_stats(db):
    _insert(db, term="TCP", score=80)
    stats = get_attempt_stats(db, "def_to_term")
    assert ("TCP", 1) in stats
    assert stats[("TCP", 1)].avg_score == 80


def test_stats_scoped_to_mode(db):
    _insert(db, term="TCP", mode="def_to_term", score=80)
    _insert(db, term="TCP", mode="term_to_def", score=50)
    d2t = get_attempt_stats(db, "def_to_term")
    t2d = get_attempt_stats(db, "term_to_def")
    assert d2t[("TCP", 1)].avg_score == 80
    assert t2d[("TCP", 1)].avg_score == 50


def test_update_attempt_score(db):
    _insert(db, term="TCP", score=0, correct=False)
    update_attempt_score(db, term="TCP", unit=1, mode="def_to_term", score=90, correct=True)
    stats = get_attempt_stats(db, "def_to_term")
    assert stats[("TCP", 1)].avg_score == 90


def test_reset_clears_all(db):
    _insert(db, term="TCP")
    _insert(db, term="UDP")
    reset_attempts(db)
    assert get_attempt_stats(db, "def_to_term") == {}


def test_weak_spots_requires_min_two_attempts(db):
    _insert(db, term="TCP", score=10, correct=False)
    assert get_weak_spots(db) == []
    _insert(db, term="TCP", score=20, correct=False)
    spots = get_weak_spots(db)
    assert len(spots) == 1
    assert spots[0].term == "TCP"


def test_weak_spots_ordered_by_avg_score(db):
    for _ in range(2):
        _insert(db, term="TCP", score=20)
        _insert(db, term="UDP", score=80)
    spots = get_weak_spots(db)
    assert spots[0].term == "TCP"


def test_get_stats_by_mode_no_filter(db):
    _insert(db, mode="def_to_term", score=70)
    rows = get_stats_by_mode(db)
    assert any(r.mode == "def_to_term" for r in rows)


def test_get_stats_by_mode_with_unit_filter(db):
    _insert(db, unit=1, score=70)
    _insert(db, unit=2, score=90)
    rows = get_stats_by_mode(db, unit=1)
    assert len(rows) == 1
    assert rows[0].total == 1
