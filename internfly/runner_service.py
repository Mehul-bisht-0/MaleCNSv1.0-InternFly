from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .specialists import validate_candidate


app = FastAPI(title="InternFly restricted runner", version="0.1.0")


class RunRequest(BaseModel):
    source: str = Field(max_length=32_000)
    tests: list[dict[str, object]] = Field(max_length=100)
    timeout_seconds: float = Field(default=5.0, ge=0.1, le=30)


@app.get("/health/live")
def health() -> dict[str, str]:
    return {"status": "alive"}


@app.post("/run")
def run(request: RunRequest) -> dict[str, object]:
    issues = validate_candidate(request.source)
    if issues:
        raise HTTPException(400, {"outcome": "policy_rejected", "issues": issues})
    harness = request.source + "\n" + """
import json, sys
tests = json.loads(sys.stdin.read())
results = []
for item in tests:
    try:
        actual = solve(item['args'][0], item['args'][1])
        results.append({'passed': actual == item['expected']})
    except BaseException as exc:
        results.append({'passed': False, 'error': type(exc).__name__})
print(json.dumps(results))
"""
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="internfly-run-") as tmp:
        path = Path(tmp) / "candidate.py"
        path.write_text(harness, encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-S", str(path)],
                input=json.dumps(request.tests), text=True, capture_output=True,
                cwd=tmp, timeout=request.timeout_seconds, env={"PYTHONHASHSEED": "0"},
            )
        except subprocess.TimeoutExpired:
            return {"outcome": "timeout", "passed": 0, "failed": len(request.tests)}
    if completed.returncode != 0:
        return {"outcome": "runtime_error", "passed": 0, "failed": len(request.tests),
                "stderr": completed.stderr[-4096:]}
    try:
        results = json.loads(completed.stdout[-65_536:])
    except json.JSONDecodeError:
        return {"outcome": "invalid_output", "passed": 0, "failed": len(request.tests)}
    passed = sum(bool(item.get("passed")) for item in results)
    return {"outcome": "solved" if passed == len(results) else "failed", "passed": passed,
            "failed": len(results) - passed, "wall_ms": round((time.perf_counter() - started) * 1000, 2)}

