from internfly.specialists import JobSpecialist
from internfly.store import EventStore


def test_events_are_idempotent(tmp_path):
    store = EventStore(str(tmp_path / "test.db"))
    from internfly.domain import Provenance
    first = store.append("test", {"x": 1}, Provenance.DETERMINISTIC_EXECUTION, idempotency_key="same")
    second = store.append("test", {"x": 2}, Provenance.DETERMINISTIC_EXECUTION, idempotency_key="same")
    assert first["event_id"] == second["event_id"]
    assert store.counts()["events"] == 1


def test_job_dedup_and_content_bound_approval(tmp_path):
    store = EventStore(str(tmp_path / "test.db"))
    jobs = JobSpecialist(store)
    result = jobs.ingest(1)
    assert result == {"discovered": 3, "deduplicated": 1}
    evaluation = jobs.evaluate_next()
    assert evaluation and evaluation["score"] >= 70
    draft = jobs.create_draft(evaluation["job_id"])
    approval = jobs.decide(draft["draft_id"], "approved", draft["content_hash"], None)
    assert approval["submission_performed"] is False

