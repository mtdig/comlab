from app.glossary import GLOSSARY


def test_homepage_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "html" in r.headers["content-type"]


def test_question_endpoint(client):
    r = client.get("/question?mode=def_to_term&unit=")
    assert r.status_code == 200


def test_grade_correct_answer(client):
    entry = GLOSSARY[0]
    r = client.post(
        "/grade",
        data={
            "term":        entry["term"],
            "unit":        str(entry["unit"]),
            "mode":        "def_to_term",
            "answer":      entry["term"],  # exact match → score 100
            "unit_filter": "",
            "expired":     "0",
            "time_taken":  "5",
        },
    )
    assert r.status_code == 200
    assert "correct" in r.text


def test_grade_wrong_answer(client):
    entry = GLOSSARY[0]
    r = client.post(
        "/grade",
        data={
            "term":        entry["term"],
            "unit":        str(entry["unit"]),
            "mode":        "def_to_term",
            "answer":      "zzz_definitely_wrong",
            "unit_filter": "",
            "expired":     "0",
            "time_taken":  "5",
        },
    )
    assert r.status_code == 200


def test_grade_expired_shows_times_up(client):
    entry = GLOSSARY[0]
    r = client.post(
        "/grade",
        data={
            "term":        entry["term"],
            "unit":        str(entry["unit"]),
            "mode":        "def_to_term",
            "answer":      "",
            "unit_filter": "",
            "expired":     "1",
            "time_taken":  "30",
        },
    )
    assert r.status_code == 200
    assert "Time&#39;s up" in r.text or "Time's up" in r.text


def test_grade_unknown_term_returns_404(client):
    r = client.post(
        "/grade",
        data={
            "term":        "NoSuchTerm99",
            "unit":        "1",
            "mode":        "def_to_term",
            "answer":      "anything",
            "unit_filter": "",
            "expired":     "0",
            "time_taken":  "5",
        },
    )
    assert r.status_code == 404


def test_api_units_returns_list(client):
    r = client.get("/api/units")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert all("unit" in u and "unit_name" in u for u in data)


def test_api_stats_empty_db(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    assert r.json() == []


def test_api_reset(client):
    entry = GLOSSARY[0]
    # add one attempt
    client.post(
        "/grade",
        data={
            "term": entry["term"], "unit": str(entry["unit"]),
            "mode": "def_to_term", "answer": entry["term"],
            "unit_filter": "", "expired": "0", "time_taken": "5",
        },
    )
    assert client.get("/api/stats").json() != []
    r = client.post("/api/reset")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert client.get("/api/stats").json() == []


def test_study_cards(client):
    r = client.get("/study/cards")
    assert r.status_code == 200
