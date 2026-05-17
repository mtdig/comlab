import time

from app.utils import to_dicts


def insert_attempt(
    conn,
    *,
    term: str,
    unit: int,
    mode: str,
    score: int,
    correct: bool,
    time_taken: int,
    expired: bool,
) -> None:
    conn.execute(
        "INSERT INTO attempts (term, unit, mode, score, correct, ts, time_taken, expired) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [term, unit, mode, score, int(correct), int(time.time()), max(0, time_taken), int(expired)],
    )


def update_attempt_score(
    conn, *, term: str, unit: int, mode: str, score: int, correct: bool
) -> None:
    conn.execute(
        """UPDATE attempts SET score = ?, correct = ?
           WHERE ts = (SELECT MAX(ts) FROM attempts WHERE term = ? AND unit = ? AND mode = ?)
             AND term = ? AND unit = ? AND mode = ?""",
        [score, int(correct), term, unit, mode, term, unit, mode],
    )


def get_attempt_stats(conn, mode: str) -> dict[tuple[str, int], dict]:
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
    return {(r["term"], r["unit"]): r for r in to_dicts(cur)}


def get_stats_by_mode(conn, unit: int = 0) -> list[dict]:
    if unit:
        cur = conn.execute(
            "SELECT mode, COUNT(*) AS total, SUM(correct) AS hits, AVG(score) AS avg_score "
            "FROM attempts WHERE unit=? GROUP BY mode",
            [unit],
        )
    else:
        cur = conn.execute(
            "SELECT mode, COUNT(*) AS total, SUM(correct) AS hits, AVG(score) AS avg_score "
            "FROM attempts GROUP BY mode"
        )
    return to_dicts(cur)


def get_weak_spots(conn, limit: int = 10) -> list[dict]:
    cur = conn.execute(
        """
        SELECT term, unit, mode,
               COUNT(*) AS attempts,
               SUM(correct) AS correct_count,
               AVG(score) AS avg_score
        FROM attempts
        GROUP BY term, unit, mode
        HAVING COUNT(*) >= 2
        ORDER BY avg_score ASC
        LIMIT ?
        """,
        [limit],
    )
    return to_dicts(cur)


def reset_attempts(conn) -> None:
    conn.execute("DELETE FROM attempts")
