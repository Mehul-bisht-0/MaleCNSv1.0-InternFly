from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Provenance(StrEnum):
    BIOLOGICAL_CONNECTIVITY = "BIOLOGICAL_CONNECTIVITY"
    SIMULATED_DYNAMICS = "SIMULATED_DYNAMICS"
    ENGINEERED_MAPPING = "ENGINEERED_MAPPING"
    LLM_GENERATED = "LLM_GENERATED"
    DETERMINISTIC_EXECUTION = "DETERMINISTIC_EXECUTION"
    FICTIONAL_ENTERTAINMENT = "FICTIONAL_ENTERTAINMENT"


class AgentMode(StrEnum):
    OFFLINE = "offline"
    SAFE_PREVIEW = "safe_preview"
    LIVE = "live"
    REPLAY = "replay"


class State(StrEnum):
    BOOT = "BOOT"
    WAKE = "WAKE"
    PLAN_DAY = "PLAN_DAY"
    SELECT_TASK = "SELECT_TASK"
    COFFEE_BREAK = "COFFEE_BREAK"
    SOLVE_DSA = "SOLVE_DSA"
    TEST_SOLUTION = "TEST_SOLUTION"
    DEBUG_SOLUTION = "DEBUG_SOLUTION"
    SEARCH_JOBS = "SEARCH_JOBS"
    EVALUATE_JOB = "EVALUATE_JOB"
    DRAFT_APPLICATION = "DRAFT_APPLICATION"
    WAITING_FOR_HUMAN_APPROVAL = "WAITING_FOR_HUMAN_APPROVAL"
    REFLECT = "REFLECT"
    PREPARE_SLEEP = "PREPARE_SLEEP"
    SLEEP = "SLEEP"
    DREAM = "DREAM"
    CONSOLIDATE_MEMORY = "CONSOLIDATE_MEMORY"
    WAKE_AGAIN = "WAKE_AGAIN"
    RECOVER_FROM_FAILURE = "RECOVER_FROM_FAILURE"


@dataclass
class AgentSnapshot:
    state: State = State.BOOT
    cycle: int = 0
    step: int = 0
    cycle_step: int = 0
    state_ticks: int = 0
    simulated_minutes: int = 420
    sleep_minutes_remaining: int = 0
    energy: float = 100.0
    stress: float = 12.0
    confidence: float = 35.0
    curiosity: float = 78.0
    dopamine: float = 50.0
    sleep_debt: float = 0.0
    caffeine_level: float = 0.0
    caffeine_crash: bool = False
    coffee_cups: int = 0
    paused: bool = False
    stopped: bool = False
    sleep_requested: bool = False
    work_items: int = 0
    last_action: str = "booting"
    current_item: str | None = None
    selected_strategy: str | None = None
    last_reward: float = 0.0
    cycle_started_at: str | None = None
    first_boot_at: str | None = None
    last_wake_at: str | None = None
    last_sleep_at: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def clamp(self) -> None:
        for name in ("energy", "stress", "confidence", "curiosity", "dopamine", "sleep_debt", "caffeine_level"):
            setattr(self, name, max(0.0, min(100.0, float(getattr(self, name)))))
        self.updated_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentSnapshot":
        copy = dict(data)
        copy["state"] = State(copy.get("state", State.BOOT))
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in copy.items() if key in allowed})


ALLOWED_TRANSITIONS: dict[State, set[State]] = {
    State.BOOT: {State.WAKE, State.RECOVER_FROM_FAILURE},
    State.WAKE: {State.PLAN_DAY},
    State.PLAN_DAY: {State.SELECT_TASK},
    State.SELECT_TASK: {State.SOLVE_DSA, State.COFFEE_BREAK, State.SEARCH_JOBS, State.REFLECT, State.PREPARE_SLEEP},
    State.COFFEE_BREAK: {State.SELECT_TASK},
    State.SOLVE_DSA: {State.TEST_SOLUTION},
    State.TEST_SOLUTION: {State.SELECT_TASK, State.DEBUG_SOLUTION},
    State.DEBUG_SOLUTION: {State.TEST_SOLUTION, State.SELECT_TASK},
    State.SEARCH_JOBS: {State.EVALUATE_JOB, State.SELECT_TASK},
    State.EVALUATE_JOB: {State.DRAFT_APPLICATION, State.SELECT_TASK},
    State.DRAFT_APPLICATION: {State.WAITING_FOR_HUMAN_APPROVAL, State.SELECT_TASK},
    State.WAITING_FOR_HUMAN_APPROVAL: {State.SELECT_TASK, State.PREPARE_SLEEP},
    State.REFLECT: {State.SELECT_TASK, State.PREPARE_SLEEP},
    State.PREPARE_SLEEP: {State.SLEEP},
    State.SLEEP: {State.DREAM},
    State.DREAM: {State.CONSOLIDATE_MEMORY},
    State.CONSOLIDATE_MEMORY: {State.WAKE_AGAIN},
    State.WAKE_AGAIN: {State.WAKE},
    State.RECOVER_FROM_FAILURE: {State.WAKE, State.PREPARE_SLEEP},
}


def assert_transition(source: State, target: State) -> None:
    if target not in ALLOWED_TRANSITIONS[source]:
        raise ValueError(f"Illegal state transition: {source} -> {target}")
