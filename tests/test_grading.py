from app.grading import build_result, grade_def_to_term
from app.utils import normalize


def test_normalize_strips_non_alphanumeric():
    assert normalize("Hello, World!") == "helloworld"
    assert normalize("TCP/IP") == "tcpip"
    assert normalize("foo-bar_baz 123") == "foobarbaz123"


def test_grade_perfect_match():
    correct, score, _ = grade_def_to_term("TCP/IP", "TCP/IP")
    assert correct is True
    assert score == 100


def test_grade_case_insensitive_perfect():
    correct, score, _ = grade_def_to_term("tcp/ip", "TCP/IP")
    assert correct is True
    assert score == 100


def test_grade_all_words_present_in_any_order():
    # all three words present in the user answer → 90
    correct, score, _ = grade_def_to_term("network local area", "Local Area Network")
    assert correct is True
    assert score == 90


def test_grade_partial_match():
    # "local area" = 2/3 words matched ≥ 0.6 → partial credit
    correct, score, msg = grade_def_to_term("local area", "Local Area Network")
    assert correct is False
    assert 0 < score < 100
    assert "Partially correct" in msg


def test_grade_wrong_answer():
    correct, score, msg = grade_def_to_term("UDP", "TCP/IP")
    assert correct is False
    assert score == 0
    assert "Incorrect" in msg


def test_build_result_correct():
    r = build_result(True, 100, "Perfect!", "TCP/IP")
    assert r["cls"] == "correct"
    assert r["icon"] == "✅"
    assert r["title"] == "Correct!"
    assert r["score"] == 100
    assert r["correct"] is True
    assert r["reference"] == "TCP/IP"


def test_build_result_partial():
    r = build_result(False, 60, "Close!", "TCP/IP")
    assert r["cls"] == "partial"
    assert r["icon"] == "🟡"


def test_build_result_wrong():
    r = build_result(False, 20, "Nope.", "TCP/IP")
    assert r["cls"] == "wrong"
    assert r["icon"] == "❌"


def test_build_result_boundary_50_is_partial():
    r = build_result(False, 50, "Edge.", "X")
    assert r["cls"] == "partial"


def test_build_result_boundary_49_is_wrong():
    r = build_result(False, 49, "Edge.", "X")
    assert r["cls"] == "wrong"
