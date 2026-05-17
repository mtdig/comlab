import re


def normalize(s: str) -> str:
    """Collapse a string to lowercase alphanumeric for fuzzy comparison."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def to_dicts(cur) -> list[dict]:
    """Convert a DuckDB cursor result to a list of row dicts."""
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
