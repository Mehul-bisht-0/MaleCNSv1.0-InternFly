from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    mode: str = os.getenv("INTERNFLY_MODE", "offline")
    database_path: str = os.getenv("INTERNFLY_DATABASE_PATH", "internfly.db")
    step_seconds: float = float(os.getenv("INTERNFLY_STEP_SECONDS", "1.0"))
    auto_start: bool = _bool("INTERNFLY_AUTO_START", True)
    runner_url: str | None = os.getenv("INTERNFLY_RUNNER_URL")
    allow_local_runner: bool = _bool("INTERNFLY_ALLOW_LOCAL_RUNNER", False)
    cors_origins: tuple[str, ...] = tuple(
        x.strip()
        for x in os.getenv("INTERNFLY_CORS_ORIGINS", "http://localhost:5173").split(",")
        if x.strip()
    )
    max_cycle_steps: int = int(os.getenv("INTERNFLY_MAX_CYCLE_STEPS", "24"))
    simulated_minutes_per_tick: int = int(os.getenv("INTERNFLY_SIM_MINUTES_PER_TICK", "20"))
    sleep_minutes: int = int(os.getenv("INTERNFLY_SLEEP_MINUTES", "300"))
    dsa_solve_ticks: int = int(os.getenv("INTERNFLY_DSA_SOLVE_TICKS", "7"))
    dsa_test_ticks: int = int(os.getenv("INTERNFLY_DSA_TEST_TICKS", "5"))
    job_search_ticks: int = int(os.getenv("INTERNFLY_JOB_SEARCH_TICKS", "7"))
    job_evaluate_ticks: int = int(os.getenv("INTERNFLY_JOB_EVALUATE_TICKS", "5"))
    job_draft_ticks: int = int(os.getenv("INTERNFLY_JOB_DRAFT_TICKS", "5"))
    coffee_ticks: int = int(os.getenv("INTERNFLY_COFFEE_TICKS", "4"))
    connectome_manifest: str | None = os.getenv("INTERNFLY_CONNECTOME_MANIFEST")
    energy_floor: float = 10.0
    sleep_debt_ceiling: float = 80.0


settings = Settings()
