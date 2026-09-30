from __future__ import annotations

import ast
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from .domain import Provenance
from .store import EventStore, canonical_json, now


PROBLEM = {
    "bank_key": "original-two-sum-indices",
    "title": "Pair With Target Sum",
    "license": "CC0 project-authored fixture",
    "topic": "hash-map",
    "difficulty": "easy",
    "statement": "Return indices of two distinct integers whose sum equals target.",
    "public_tests": [([2, 7, 11, 15], 9, [0, 1]), ([3, 2, 4], 6, [1, 2])],
    "hidden_tests": [([3, 3], 6, [0, 1]), ([-1, -2, -3, -4, -5], -8, [2, 4])],
}


FIXTURE_CODE = """def solve(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        wanted = target - value
        if wanted in seen:
            return [seen[wanted], index]
        seen[value] = index
    return []
"""


FORBIDDEN_AST = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}


def validate_candidate(source: str) -> list[str]:
    issues: list[str] = []
    if len(source.encode()) > 32_000:
        issues.append("source_too_large")
        return issues
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ["syntax_error"]
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_AST):
            issues.append(f"forbidden_{node.__class__.__name__.lower()}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
            issues.append(f"forbidden_call_{node.func.id}")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "solve" for n in tree.body):
        issues.append("missing_solve_function")
    return sorted(set(issues))


@dataclass
class TestOutcome:
    passed: int
    failed: int
    outcome: str
    runtime_ms: float
    memory_bytes: int
    failure_category: str | None = None


class DeterministicFixtureRunner:
    """Safe fake runner used offline; it never evaluates source code.

    The fixture recognizes the pinned code hash and calculates expected behavior
    with a trusted implementation. Arbitrary candidates require runner_service.
    """

    def run(self, source: str, problem: dict[str, Any]) -> TestOutcome:
        issues = validate_candidate(source)
        if issues:
            return TestOutcome(0, 1, "policy_rejected", 0.0, 0, issues[0])
        if hashlib.sha256(source.encode()).hexdigest() != hashlib.sha256(FIXTURE_CODE.encode()).hexdigest():
            return TestOutcome(0, 1, "runner_required", 0.0, 0, "safe_offline_refusal")
        tests = problem["public_tests"] + problem["hidden_tests"]
        return TestOutcome(len(tests), 0, "solved", 1.2, 8_388_608)


class RemoteSandboxRunner:
    """Calls the internal-only, resource-limited runner container."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def run(self, source: str, problem: dict[str, Any]) -> TestOutcome:
        tests = [
            {"args": [numbers, target], "expected": expected}
            for numbers, target, expected in problem["public_tests"] + problem["hidden_tests"]
        ]
        try:
            response = httpx.post(
                f"{self.base_url}/run",
                json={"source": source, "tests": tests, "timeout_seconds": 5},
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return TestOutcome(0, len(tests), "runner_unavailable", 0.0, 0, type(exc).__name__)
        return TestOutcome(
            int(data.get("passed", 0)), int(data.get("failed", len(tests))),
            str(data.get("outcome", "failed")), float(data.get("wall_ms", 0)),
            int(data.get("memory_bytes", 0)), data.get("failure_category"),
        )


class DsaSpecialist:
    def __init__(self, store: EventStore, runner_url: str | None = None) -> None:
        self.store = store
        self.runner = RemoteSandboxRunner(runner_url) if runner_url else DeterministicFixtureRunner()

    def solve(self, cycle: int, strategy: str) -> dict[str, Any]:
        attempt_no = 1 + self.store.query(
            "SELECT COUNT(*) AS n FROM attempts WHERE cycle=? AND problem_key=?",
            (cycle, PROBLEM["bank_key"]),
        )[0]["n"]
        source = FIXTURE_CODE
        result = self.runner.run(source, PROBLEM)
        attempt_id = str(uuid.uuid4())
        code_hash = hashlib.sha256(source.encode()).hexdigest()
        self.store.execute(
            """INSERT INTO attempts(attempt_id,cycle,problem_key,attempt_no,strategy,outcome,
               runtime_ms,memory_bytes,code_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (attempt_id, cycle, PROBLEM["bank_key"], attempt_no, strategy, result.outcome,
             result.runtime_ms, result.memory_bytes, code_hash, now()),
        )
        payload = {
            "attempt_id": attempt_id,
            "problem_key": PROBLEM["bank_key"],
            "title": PROBLEM["title"],
            "strategy": strategy,
            "attempt_no": attempt_no,
            "public": {"passed": min(result.passed, len(PROBLEM["public_tests"])), "failed": 0},
            "hidden": {"passed": max(0, result.passed - len(PROBLEM["public_tests"])), "failed": result.failed},
            "outcome": result.outcome,
            "runtime_ms": result.runtime_ms,
            "memory_bytes": result.memory_bytes,
            "failure_category": result.failure_category,
            "hidden_test_details_exposed": False,
        }
        self.store.append(
            "dsa.attempt_tested", payload, Provenance.DETERMINISTIC_EXECUTION,
            actor="dsa_specialist", idempotency_key=f"cycle:{cycle}:dsa:{attempt_no}",
        )
        return payload


FICTIONAL_JOBS = [
    {
        "external_id": "bytebramble-001", "company": "ByteBramble Labs",
        "title": "Software Engineering Intern", "location": "Remote (Fictional)",
        "description": "Build Python services and test data structures with a kind team.",
        "required": ["python", "data structures"], "preferred": ["testing", "apis"],
    },
    {
        "external_id": "wingstack-002", "company": "WingStack Systems",
        "title": "Backend Intern", "location": "Remote (Fictional)",
        "description": "Create reliable APIs, metrics, and delightfully boring runbooks.",
        "required": ["python", "apis"], "preferred": ["sql", "docker"],
    },
    {
        "external_id": "bytebramble-001", "company": "ByteBramble Labs",
        "title": "Software Engineering Intern", "location": "Remote (Fictional)",
        "description": "Build Python services and test data structures with a kind team.",
        "required": ["python", "data structures"], "preferred": ["testing", "apis"],
    },
]

PROFILE = {
    "profile_id": "fictional-fly-v1",
    "name": "I. Fly",
    "fictional": True,
    "skills": ["python", "data structures", "testing", "apis", "sql"],
    "facts": {
        "practice": "Practices project-authored data-structure problems in Python.",
        "reliability": "Built this offline simulation with bounded, auditable workflows.",
    },
}


class JobSpecialist:
    def __init__(self, store: EventStore) -> None:
        self.store = store

    def ingest(self, cycle: int) -> dict[str, int]:
        discovered = deduplicated = 0
        for raw in FICTIONAL_JOBS:
            discovered += 1
            identity = f"fictional:{raw['external_id']}"
            existing = self.store.query("SELECT job_id FROM jobs WHERE canonical_identity=?", (identity,))
            if existing:
                deduplicated += 1
                self.store.append(
                    "job.duplicate_detected", {"canonical_identity": identity, "cycle": cycle},
                    Provenance.DETERMINISTIC_EXECUTION, actor="job_specialist",
                    idempotency_key=f"cycle:{cycle}:duplicate:{identity}",
                )
                continue
            job_id = str(uuid.uuid4())
            self.store.execute(
                """INSERT INTO jobs(job_id,canonical_identity,company,title,location,description,
                   source,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                (job_id, identity, raw["company"], raw["title"], raw["location"],
                 raw["description"], "fictional_fixture", now()),
            )
            self.store.append(
                "job.discovered", {"job_id": job_id, "company": raw["company"], "fictional": True},
                Provenance.FICTIONAL_ENTERTAINMENT, actor="job_specialist",
                idempotency_key=f"job-discovered:{identity}",
            )
        return {"discovered": discovered, "deduplicated": deduplicated}

    def evaluate_next(self) -> dict[str, Any] | None:
        rows = self.store.query("SELECT * FROM jobs WHERE score IS NULL ORDER BY created_at LIMIT 1")
        if not rows:
            return None
        job = rows[0]
        raw = next(item for item in FICTIONAL_JOBS if f"fictional:{item['external_id']}" == job["canonical_identity"])
        required_overlap = len(set(raw["required"]) & set(PROFILE["skills"])) / max(1, len(raw["required"]))
        preferred_overlap = len(set(raw["preferred"]) & set(PROFILE["skills"])) / max(1, len(raw["preferred"]))
        components = {
            "required_skills": 30 * required_overlap,
            "preferred_skills": 20 * preferred_overlap,
            "location": 15, "eligibility": 10, "interest": 8,
            "learning": 4, "freshness": 5, "effort_inverse": 4,
        }
        score = round(sum(components.values()), 1)
        decision = "draft" if score >= 70 else "skip"
        self.store.execute("UPDATE jobs SET score=?,decision=? WHERE job_id=?", (score, decision, job["job_id"]))
        result = {"job_id": job["job_id"], "company": job["company"], "title": job["title"],
                  "score": score, "components": components, "decision": decision, "fictional": True}
        self.store.append("job.evaluated", result, Provenance.DETERMINISTIC_EXECUTION, actor="job_specialist")
        return result

    def create_draft(self, job_id: str) -> dict[str, Any]:
        existing = self.store.query("SELECT * FROM drafts WHERE job_id=? ORDER BY version DESC LIMIT 1", (job_id,))
        if existing:
            return self._decode_draft(existing[0])
        job = self.store.query("SELECT * FROM jobs WHERE job_id=?", (job_id,))[0]
        content = {
            "cover_letter": (
                f"Dear {job['company']} team,\n\nI am applying for the fictional {job['title']} role. "
                f"{PROFILE['facts']['practice']} {PROFILE['facts']['reliability']}\n\n"
                "This is a local demonstration draft and will not be submitted automatically."
            ),
            "resume_suggestions": ["Emphasize Python practice", "Describe testing and reliability work"],
        }
        evidence = {
            "Practices project-authored data-structure problems in Python.": "facts.practice",
            "Built this offline simulation with bounded, auditable workflows.": "facts.reliability",
        }
        content_hash = hashlib.sha256(canonical_json(content).encode()).hexdigest()
        draft_id = str(uuid.uuid4())
        self.store.execute(
            """INSERT INTO drafts(draft_id,job_id,version,status,content,evidence_map,
               unsupported_claims,content_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
            (draft_id, job_id, 1, "pending", canonical_json(content), canonical_json(evidence), "[]", content_hash, now()),
        )
        payload = {"draft_id": draft_id, "job_id": job_id, "company": job["company"], "version": 1,
                   "status": "pending", "content_hash": content_hash, "unsupported_claims": [], "fictional": True}
        self.store.append("application.draft_created", payload, Provenance.LLM_GENERATED, actor="fake_llm")
        return {**payload, "content": content, "evidence_map": evidence}

    @staticmethod
    def _decode_draft(row: dict[str, Any]) -> dict[str, Any]:
        item = dict(row)
        for key in ("content", "evidence_map", "unsupported_claims"):
            item[key] = json.loads(item[key])
        return item

    def list_jobs(self) -> list[dict[str, Any]]:
        return self.store.query("SELECT * FROM jobs ORDER BY score DESC,created_at DESC")

    def list_drafts(self) -> list[dict[str, Any]]:
        rows = self.store.query(
            """SELECT d.*,j.company,j.title FROM drafts d JOIN jobs j ON j.job_id=d.job_id
               ORDER BY d.created_at DESC"""
        )
        return [self._decode_draft(row) for row in rows]

    def decide(self, draft_id: str, decision: str, expected_hash: str, reason: str | None) -> dict[str, Any]:
        rows = self.store.query("SELECT * FROM drafts WHERE draft_id=?", (draft_id,))
        if not rows:
            raise KeyError("draft_not_found")
        draft = rows[0]
        if draft["content_hash"] != expected_hash:
            raise ValueError("stale_content_hash")
        if json.loads(draft["unsupported_claims"]):
            raise ValueError("unsupported_claims_block_approval")
        if decision not in {"approved", "rejected"}:
            raise ValueError("invalid_decision")
        approval_id = str(uuid.uuid4())
        self.store.execute(
            "INSERT INTO approvals VALUES(?,?,?,?,?,?)",
            (approval_id, draft_id, expected_hash, decision, reason, now()),
        )
        self.store.execute("UPDATE drafts SET status=? WHERE draft_id=?", (decision, draft_id))
        payload = {"approval_id": approval_id, "draft_id": draft_id, "decision": decision,
                   "content_hash": expected_hash, "submission_performed": False}
        self.store.append("application.approval_decided", payload, Provenance.DETERMINISTIC_EXECUTION,
                          actor="human_owner", idempotency_key=f"approval:{draft_id}:{expected_hash}")
        return payload


class SleepSpecialist:
    DREAMS = [
        "I was trapped in a binary tree where every leaf was an unpaid internship. I escaped in O(n).",
        "A recruiter asked for five years of photosynthesis. I offered strong debugging fundamentals instead.",
        "Dynamic programming tucked me into a memoization table and promised each nightmare would run once.",
    ]

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def dream(self, cycle: int) -> str:
        text = self.DREAMS[cycle % len(self.DREAMS)]
        self.store.execute("INSERT INTO dreams VALUES(?,?,?,?)", (str(uuid.uuid4()), cycle, text, now()))
        self.store.append("sleep.dream_generated", {"cycle": cycle, "text": text, "fictional": True},
                          Provenance.FICTIONAL_ENTERTAINMENT, actor="fake_llm",
                          idempotency_key=f"cycle:{cycle}:dream")
        return text

    def consolidate(self, cycle: int, reward: float, plasticity: dict[str, Any]) -> dict[str, Any]:
        lesson = {
            "summary": "Check complements before inserting the current value into the hash map.",
            "hidden_test_content_stored": False,
            "source_cycle": cycle,
        }
        memory_id = str(uuid.uuid4())
        self.store.execute(
            "INSERT INTO memories VALUES(?,?,?,?,?,?,?)",
            (memory_id, "semantic", canonical_json(lesson), 0.8, 0.9, 0, now()),
        )
        report = {"memory_id": memory_id, "reward": reward, "plasticity": plasticity,
                  "wake_plan": "Review hash-map invariants, then inspect one fictional internship."}
        self.store.append("sleep.memory_consolidated", report, Provenance.ENGINEERED_MAPPING,
                          actor="sleep_specialist", idempotency_key=f"cycle:{cycle}:consolidation")
        return report
