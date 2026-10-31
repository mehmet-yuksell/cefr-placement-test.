import pytest

from placement import storage
from placement.models import Response
from placement.scoring import ScoredResponse, score_responses


@pytest.fixture
def conn(tmp_path):
    connection = storage.connect(tmp_path / "t.db")
    yield connection
    connection.close()


def test_email_normalisation_and_hashing(tmp_path):
    key = storage.load_or_create_key(tmp_path / "k")
    assert storage.load_or_create_key(tmp_path / "k") == key
    assert storage.hash_email("  Ali@Example.COM ", key) == storage.hash_email("ali@example.com", key)
    assert storage.hash_email("ali@example.com", key) != storage.hash_email("ali@example.com", b"other")
    assert "@" not in storage.hash_email("ali@example.com", key)
    with pytest.raises(ValueError):
        storage.normalise_email("not-an-email")


def test_session_lifecycle(conn):
    user = "u1"
    assert storage.next_attempt_no(conn, user) == 1
    storage.create_session(conn, session_id="s1", user_hash=user, attempt_no=1, mode="adaptive", seed=7,
                           test_length=28)
    for pos, item in enumerate(["A1-CLZ-001", "A2-CLZ-001"]):
        storage.record_response(conn, "s1", Response(item, "x", pos == 0, 3.5, 1, pos), item_version=1)
    assert storage.seen_items(conn, user) == {"A1-CLZ-001": 1, "A2-CLZ-001": 1}
    assert storage.exposure_counts(conn) == {"A1-CLZ-001": 1, "A2-CLZ-001": 1}

    assert storage.mark_abandoned(conn, user) == 1
    assert storage.session_row(conn, "s1")["status"] == "abandoned"
    assert storage.next_attempt_no(conn, user) == 2

    storage.create_session(conn, session_id="s2", user_hash=user, attempt_no=2, mode="adaptive", seed=8,
                           test_length=28)
    storage.record_response(conn, "s2", Response("A1-CLZ-001", "x", True, 2.0, 1, 0), item_version=1)
    result = score_responses([ScoredResponse(b=0.0, correct=True)] * 12, complete=True)
    storage.finish_session(conn, "s2", status="completed", result=result, flags=["repeat"], engine_state={"a": 1})
    row = storage.session_row(conn, "s2")
    assert row["status"] == "completed" and row["level"] == result.level and row["flags_json"] == '["repeat"]'
    assert storage.seen_items(conn, user)["A1-CLZ-001"] == 2
    assert storage.exposure_counts(conn)["A1-CLZ-001"] == 2
    storage.finish_session(conn, "s1", status="abandoned", result=None, flags=[], engine_state={})
    assert storage.session_row(conn, "s1")["theta"] is None
    with pytest.raises(ValueError):
        storage.finish_session(conn, "s1", status="in_progress", result=None, flags=[], engine_state={})
    assert storage.session_row(conn, "nope") is None


def test_no_plaintext_email_in_database(tmp_path):
    conn = storage.connect(tmp_path / "t.db")
    key = storage.load_or_create_key(tmp_path / "k")
    user = storage.hash_email("someone@example.org", key)
    storage.create_session(conn, session_id="s", user_hash=user, attempt_no=1, mode="fixed", seed=1, test_length=28)
    conn.close()
    assert b"someone@example.org" not in (tmp_path / "t.db").read_bytes()
