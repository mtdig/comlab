from dataclasses import dataclass


@dataclass
class AttemptStats:
    """Per-(term, unit) statistics used for spaced-repetition weighting."""
    avg_score:     float
    total_expired: int
    avg_time:      float


@dataclass
class ModeStats:
    """Aggregate stats for a single quiz mode, returned by /api/stats."""
    mode:      str
    total:     int
    hits:      int
    avg_score: float


@dataclass
class WeakSpot:
    """A poorly-performing term, returned by /api/weak_spots."""
    term:          str
    unit:          int
    mode:          str
    attempts:      int
    correct_count: int
    avg_score:     float
