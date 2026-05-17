from app.selector import _select_from_pool

POOL = [
    {"term": "A", "unit": 1, "unit_name": "Basics", "definition": "def A"},
    {"term": "B", "unit": 1, "unit_name": "Basics", "definition": "def B"},
    {"term": "C", "unit": 1, "unit_name": "Basics", "definition": "def C"},
]


def _stats(*terms, score=100.0, expired=0, avg_time=5.0):
    return {
        (t, 1): {"avg_score": score, "total_expired": expired, "avg_time": avg_time}
        for t in terms
    }


def test_phase1_picks_only_unseen():
    stats = _stats("A")  # A already seen; B and C are unseen
    results = {_select_from_pool(POOL, stats)["term"] for _ in range(200)}
    assert "A" not in results
    assert results <= {"B", "C"}


def test_phase1_empty_stats_allows_any():
    results = {_select_from_pool(POOL, {})["term"] for _ in range(50)}
    assert results <= {"A", "B", "C"}


def test_phase2_returns_from_pool_when_all_seen():
    stats = _stats("A", "B", "C")
    result = _select_from_pool(POOL, stats)
    assert result["term"] in {"A", "B", "C"}


def test_phase2_low_score_picked_more_often():
    stats = {
        ("A", 1): {"avg_score": 0.0,   "total_expired": 0, "avg_time": 5.0},
        ("B", 1): {"avg_score": 100.0, "total_expired": 0, "avg_time": 5.0},
        ("C", 1): {"avg_score": 100.0, "total_expired": 0, "avg_time": 5.0},
    }
    counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    for _ in range(1000):
        counts[_select_from_pool(POOL, stats)["term"]] += 1
    # A (score=0) should be picked much more often than B or C (score=100)
    assert counts["A"] > counts["B"] * 1.5


def test_phase2_many_expireds_increases_weight():
    stats = {
        ("A", 1): {"avg_score": 100.0, "total_expired": 10, "avg_time": 5.0},
        ("B", 1): {"avg_score": 100.0, "total_expired": 0,  "avg_time": 5.0},
        ("C", 1): {"avg_score": 100.0, "total_expired": 0,  "avg_time": 5.0},
    }
    counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    for _ in range(1000):
        counts[_select_from_pool(POOL, stats)["term"]] += 1
    # A (many expireds) should be picked significantly more often
    assert counts["A"] > counts["B"] * 1.5
