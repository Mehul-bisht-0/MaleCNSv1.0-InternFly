from fastapi.testclient import TestClient

from internfly.runner_service import app
from internfly.specialists import FIXTURE_CODE


def test_runner_executes_candidate_against_supplied_tests():
    client = TestClient(app)
    response = client.post("/run", json={
        "source": FIXTURE_CODE,
        "tests": [{"args": [[2, 7, 11, 15], 9], "expected": [0, 1]}],
        "timeout_seconds": 2,
    })
    assert response.status_code == 200
    assert response.json()["outcome"] == "solved"


def test_runner_rejects_imports():
    client = TestClient(app)
    response = client.post("/run", json={
        "source": "import os\ndef solve(a, b): return []",
        "tests": [],
    })
    assert response.status_code == 400

