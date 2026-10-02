from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Settings
from .connectome import SparseRateController
from .domain import AgentSnapshot, Provenance, State, assert_transition
from .specialists import DsaSpecialist, JobSpecialist, PROBLEM, SleepSpecialist
from .store import EventStore


class Orchestrator:
    def __init__(self, store: EventStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        root = Path(__file__).resolve().parents[1]
        generated = root / "data/generated/malecns-subgraph.json"
        manifest = Path(settings.connectome_manifest) if settings.connectome_manifest else (
            generated if generated.exists() else root / "data/connectome/manifests/dev-subgraph.json"
        )
        self.controller = SparseRateController(manifest)
        self.dsa = DsaSpecialist(store, settings.runner_url)
        self.jobs = JobSpecialist(store)
        self.sleep = SleepSpecialist(store)
        self.snapshot = store.load_snapshot() or AgentSnapshot()
        self._thread: threading.Thread | None = None
        self._shutdown = threading.Event()
        self._lock = threading.RLock()
        self._last_pulse_at = 0.0
        self.latest_neural: dict[str, Any] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._shutdown.clear()
        self._thread = threading.Thread(target=self._loop, name="internfly-orchestrator", daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        self._shutdown.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.store.save_snapshot(self.snapshot)

    def command(self, action: str) -> AgentSnapshot:
        with self._lock:
            if action == "pause":
                self.snapshot.paused = True
                self.snapshot.last_action = "paused by owner"
            elif action == "resume":
                self.snapshot.paused = False
                self.snapshot.stopped = False
                self.snapshot.last_action = "resumed by owner"
            elif action == "sleep-now":
                self.snapshot.sleep_requested = True
                self.snapshot.last_action = "sleep requested by owner"
            elif action == "emergency-stop":
                self.snapshot.stopped = True
                self.snapshot.paused = True
                self.snapshot.last_action = "emergency stopped"
            else:
                raise ValueError("unknown_command")
            self.snapshot.clamp()
            self.store.append(f"owner.{action}", {"state": self.snapshot.state.value},
                              Provenance.DETERMINISTIC_EXECUTION, actor="human_owner")
            self.store.save_snapshot(self.snapshot)
            return self.snapshot

    def _loop(self) -> None:
        while not self._shutdown.is_set():
            self.pulse()
            self._shutdown.wait(self.settings.step_seconds)

    def pulse(self) -> bool:
        """Advance at most once per configured interval.

        Persistent deployments call this from the background loop. Serverless
        deployments call it from active API/WebSocket traffic, where a daemon
        thread cannot be relied upon to keep running between invocations.
        """
        with self._lock:
            now = time.monotonic()
            if now - self._last_pulse_at < self.settings.step_seconds:
                return False
            self._last_pulse_at = now
            if self.snapshot.paused or self.snapshot.stopped:
                return False
            try:
                self.tick()
            except Exception as exc:
                self.store.append(
                    "system.step_failed",
                    {"error": type(exc).__name__, "message": str(exc)[:300]},
                    Provenance.DETERMINISTIC_EXECUTION,
                    actor="watchdog",
                )
                if self.snapshot.state != State.RECOVER_FROM_FAILURE:
                    self._transition(State.RECOVER_FROM_FAILURE, "recovering from bounded failure")
            return True

    def _transition(self, target: State, description: str) -> None:
        source = self.snapshot.state
        assert_transition(source, target)
        self.snapshot.state = target
        self.snapshot.state_ticks = 0
        self.snapshot.step += 1
        self.snapshot.cycle_step += 1
        self.snapshot.last_action = description
        self.snapshot.clamp()
        self.store.append(
            "agent.state_transition",
            {"from": source.value, "to": target.value, "cycle": self.snapshot.cycle,
             "step": self.snapshot.step, "description": description},
            Provenance.DETERMINISTIC_EXECUTION,
            idempotency_key=f"transition:{self.snapshot.step}:{source.value}:{target.value}",
        )
        self.store.save_snapshot(self.snapshot)

    def _hold(self, description: str) -> None:
        self.snapshot.last_action = description
        self.snapshot.clamp()
        self.store.save_snapshot(self.snapshot)

    def _must_sleep(self) -> bool:
        return (
            self.snapshot.sleep_requested
            or self.snapshot.energy <= self.settings.energy_floor
            or self.snapshot.sleep_debt >= self.settings.sleep_debt_ceiling
            or self.snapshot.cycle_step >= self.settings.max_cycle_steps
            or self.snapshot.work_items >= 4
        )

    def _observe(self) -> dict[str, float]:
        return {key: float(getattr(self.snapshot, key)) for key in
                ("energy", "stress", "confidence", "curiosity", "dopamine", "sleep_debt", "caffeine_level")}

    def _advance_virtual_clock_and_metabolism(self) -> None:
        self.snapshot.state_ticks += 1
        self.snapshot.simulated_minutes = (
            self.snapshot.simulated_minutes + self.settings.simulated_minutes_per_tick
        ) % 1440
        if self.snapshot.state in {State.SLEEP, State.DREAM, State.CONSOLIDATE_MEMORY}:
            self.snapshot.sleep_minutes_remaining = max(
                0,
                self.snapshot.sleep_minutes_remaining - self.settings.simulated_minutes_per_tick,
            )
        previous_caffeine = self.snapshot.caffeine_level
        decay = 5.0 if self.snapshot.state in {State.SLEEP, State.DREAM, State.CONSOLIDATE_MEMORY} else 2.5
        self.snapshot.caffeine_level = max(0.0, self.snapshot.caffeine_level - decay)
        if self.snapshot.caffeine_level >= 45:
            self.snapshot.energy += 0.8
            self.snapshot.curiosity += 0.25
            self.snapshot.stress += 0.35
            self.snapshot.sleep_debt += 0.45
        if previous_caffeine >= 25 > self.snapshot.caffeine_level and not self.snapshot.caffeine_crash:
            self.snapshot.caffeine_crash = True
            self.snapshot.energy -= 18
            self.snapshot.confidence -= 6
            self.snapshot.stress += 10
            self.store.append(
                "agent.caffeine_crash",
                {"cycle": self.snapshot.cycle, "caffeine_level": self.snapshot.caffeine_level,
                 "fictional_model": True},
                Provenance.FICTIONAL_ENTERTAINMENT,
                actor="metabolism_model",
            )
        self.snapshot.clamp()

    def tick(self) -> None:
        self._advance_virtual_clock_and_metabolism()
        state = self.snapshot.state
        if state == State.BOOT:
            if not self.snapshot.first_boot_at:
                self.snapshot.first_boot_at = datetime.now(UTC).isoformat()
                self.store.append("agent.booted", {"mode": self.settings.mode}, Provenance.DETERMINISTIC_EXECUTION)
            self._transition(State.WAKE, "boot complete")
        elif state in {State.WAKE, State.WAKE_AGAIN}:
            if state == State.WAKE_AGAIN:
                self._transition(State.WAKE, "durable wake timer fired")
                return
            self.snapshot.cycle += 1
            self.snapshot.cycle_step = 0
            self.snapshot.work_items = 0
            self.snapshot.sleep_requested = False
            self.snapshot.cycle_started_at = datetime.now(UTC).isoformat()
            self.snapshot.last_wake_at = self.snapshot.cycle_started_at
            self.snapshot.energy = min(100, self.snapshot.energy + 55)
            self.snapshot.sleep_debt = max(0, self.snapshot.sleep_debt - 65)
            self._transition(State.PLAN_DAY, "reading the wake-up plan")
        elif state == State.PLAN_DAY:
            self.store.append("cycle.plan_created", {"cycle": self.snapshot.cycle,
                "objectives": ["practice one DSA problem", "inspect fictional internships", "sleep on time"],
                "provider": "deterministic_fake"}, Provenance.LLM_GENERATED,
                idempotency_key=f"cycle:{self.snapshot.cycle}:plan")
            self._transition(State.SELECT_TASK, "plan is bounded and ready")
        elif state == State.SELECT_TASK:
            if self._must_sleep():
                self._transition(State.PREPARE_SLEEP, "policy forced sleep before another task")
                return
            step = self.controller.step(self._observe(), seed=self.snapshot.cycle * 10_000 + self.snapshot.step)
            self.latest_neural = {
                "action_scores": step.action_scores, "selected_preference": step.selected_preference,
                "active_neurons": step.active_neurons, "mean_activity": step.mean_activity,
                "peak_activity": step.peak_activity, "region_activity": step.region_activity,
                "caffeine_input_gain": round(step.caffeine_input_gain, 4),
                "caffeine_noise_amplitude": round(step.caffeine_noise_amplitude, 4),
                "caffeine_notice": (
                    "Engineered entertainment model: caffeine increases controller input gain and seeded noise; "
                    "it is not a biological dosage model."
                ),
                "neuron_activity": [round(value, 5) for value in self.controller.activity],
                "saturation_warning": step.saturation_warning, "notice": step.provenance_notice,
                "manifest_hash": self.controller.manifest_hash,
            }
            self.store.append("connectome.controller_step", self.latest_neural,
                              Provenance.SIMULATED_DYNAMICS, actor="connectome_controller")
            # Safety/coverage gate ensures both bounded specialists get time; neural preference is preserved in audit.
            if self.snapshot.work_items == 0:
                target = State.SOLVE_DSA
            elif self.snapshot.work_items == 1:
                target = State.COFFEE_BREAK
            elif self.snapshot.work_items == 2:
                target = State.SEARCH_JOBS
            else:
                target = State.REFLECT
            self._transition(target, f"controller preferred {step.selected_preference}; coverage policy selected {target.value}")
        elif state == State.SOLVE_DSA:
            self.snapshot.current_item = PROBLEM["title"]
            strategies = ["hash-map", "two-pointer", "brute-force"]
            score = self.latest_neural.get("action_scores", {}).get("SOLVE_DSA", 0)
            self.snapshot.selected_strategy = strategies[int(abs(score) * 1000) % len(strategies)]
            if self.snapshot.state_ticks < self.settings.dsa_solve_ticks:
                self._hold(
                    f"working through {self.snapshot.selected_strategy} reasoning "
                    f"({self.snapshot.state_ticks}/{self.settings.dsa_solve_ticks})"
                )
                return
            self._transition(State.TEST_SOLUTION, f"generated a {self.snapshot.selected_strategy} candidate")
        elif state == State.TEST_SOLUTION:
            if self.snapshot.state_ticks < self.settings.dsa_test_ticks:
                self._hold(
                    f"running bounded public and hidden tests "
                    f"({self.snapshot.state_ticks}/{self.settings.dsa_test_ticks})"
                )
                return
            result = self.dsa.solve(self.snapshot.cycle, self.snapshot.selected_strategy or "hash-map")
            solved = result["outcome"] == "solved"
            self.snapshot.last_reward = 0.8 if solved else -0.35
            self.snapshot.energy -= 12
            self.snapshot.sleep_debt += 10
            self.snapshot.confidence += 8 if solved else -6
            self.snapshot.stress += -4 if solved else 8
            self.snapshot.dopamine += 10 if solved else -5
            self.snapshot.work_items += 1
            self.snapshot.current_item = None
            self.snapshot.clamp()
            self._transition(State.SELECT_TASK if solved else State.DEBUG_SOLUTION,
                             "tests passed" if solved else "tests failed; bounded debug available")
        elif state == State.DEBUG_SOLUTION:
            self._transition(State.TEST_SOLUTION, "applied one bounded debugging revision")
        elif state == State.COFFEE_BREAK:
            if self.snapshot.state_ticks == 1:
                self.snapshot.coffee_cups += 2
                self.snapshot.caffeine_level = min(100, self.snapshot.caffeine_level + 68)
                self.snapshot.caffeine_crash = False
                self.snapshot.energy += 24
                self.snapshot.confidence += 7
                self.snapshot.curiosity += 5
                self.snapshot.dopamine += 14
                self.snapshot.stress += 12
                self.snapshot.sleep_debt += 16
                self.snapshot.clamp()
                self.store.append(
                    "agent.coffee_consumed",
                    {"cycle": self.snapshot.cycle, "cups": 2,
                     "caffeine_units": 68, "fictional_model": True,
                     "notice": "Entertainment simulation; not health or dosage guidance."},
                    Provenance.FICTIONAL_ENTERTAINMENT,
                    actor="coffee_station",
                    idempotency_key=f"cycle:{self.snapshot.cycle}:coffee",
                )
            if self.snapshot.state_ticks < self.settings.coffee_ticks:
                self._hold(
                    f"consuming an inadvisable fictional amount of coffee "
                    f"({self.snapshot.state_ticks}/{self.settings.coffee_ticks})"
                )
                return
            self.snapshot.work_items += 1
            self._transition(State.SELECT_TASK, "caffeine entered the simulated controller state")
        elif state == State.SEARCH_JOBS:
            if self.snapshot.state_ticks < self.settings.job_search_ticks:
                self._hold(
                    f"carefully scanning permitted fictional listings "
                    f"({self.snapshot.state_ticks}/{self.settings.job_search_ticks})"
                )
                return
            summary = self.jobs.ingest(self.snapshot.cycle)
            self.snapshot.current_item = f"{summary['discovered']} fictional listings"
            self._transition(State.EVALUATE_JOB, "permitted fictional source ingested and deduplicated")
        elif state == State.EVALUATE_JOB:
            if self.snapshot.state_ticks < self.settings.job_evaluate_ticks:
                self._hold(
                    f"scoring evidence and eligibility "
                    f"({self.snapshot.state_ticks}/{self.settings.job_evaluate_ticks})"
                )
                return
            result = self.jobs.evaluate_next()
            if result and result["decision"] == "draft":
                self.snapshot.current_item = f"{result['title']} at {result['company']}"
                self._transition(State.DRAFT_APPLICATION, f"explicit rubric score {result['score']}/100")
            else:
                self.snapshot.work_items += 1
                self._transition(State.SELECT_TASK, "no eligible undrafted listing")
        elif state == State.DRAFT_APPLICATION:
            if self.snapshot.state_ticks < self.settings.job_draft_ticks:
                self._hold(
                    f"writing a claim-by-claim truthful draft "
                    f"({self.snapshot.state_ticks}/{self.settings.job_draft_ticks})"
                )
                return
            job_id = self.store.query("SELECT job_id FROM jobs WHERE decision='draft' ORDER BY score DESC LIMIT 1")[0]["job_id"]
            self.jobs.create_draft(job_id)
            self.snapshot.energy -= 8
            self.snapshot.sleep_debt += 6
            self.snapshot.work_items += 1
            self._transition(State.WAITING_FOR_HUMAN_APPROVAL, "truthful local draft queued; no submission performed")
        elif state == State.WAITING_FOR_HUMAN_APPROVAL:
            self.snapshot.current_item = None
            self._transition(State.SELECT_TASK, "approval inbox is nonblocking")
        elif state == State.REFLECT:
            self.store.append("cycle.reflected", {"cycle": self.snapshot.cycle,
                "summary": "Hash maps were kind; duplicate listings were less subtle than they believed.",
                "fictional_tone": True}, Provenance.LLM_GENERATED,
                idempotency_key=f"cycle:{self.snapshot.cycle}:reflection")
            self.snapshot.work_items += 1
            self._transition(State.SELECT_TASK, "bounded reflection complete")
        elif state == State.PREPARE_SLEEP:
            self.snapshot.current_item = None
            self.snapshot.sleep_minutes_remaining = self.settings.sleep_minutes
            self._transition(State.SLEEP, "atomic work drained; beginning functional sleep")
        elif state == State.SLEEP:
            self.snapshot.last_sleep_at = datetime.now(UTC).isoformat()
            if self.snapshot.sleep_minutes_remaining > 120:
                self._hold(
                    f"deep sleep; {self.snapshot.sleep_minutes_remaining / 60:.1f} simulated hours remain"
                )
                return
            self._transition(State.DREAM, "important events replayed")
        elif state == State.DREAM:
            self.sleep.dream(self.snapshot.cycle)
            self._transition(State.CONSOLIDATE_MEMORY, "fictional dream generated; excluded from factual memory")
        elif state == State.CONSOLIDATE_MEMORY:
            if self.snapshot.sleep_minutes_remaining > 0:
                self._hold(
                    f"consolidating memory; {self.snapshot.sleep_minutes_remaining / 60:.1f} simulated hours remain"
                )
                return
            plasticity = self.controller.apply_sleep_update(self.snapshot.last_reward)
            self.sleep.consolidate(self.snapshot.cycle, self.snapshot.last_reward, plasticity)
            self.snapshot.energy = min(100, self.snapshot.energy + 25)
            self.snapshot.stress = max(0, self.snapshot.stress - 12)
            self.snapshot.sleep_debt = max(0, self.snapshot.sleep_debt - 30)
            self.store.append("cycle.completed", {"cycle": self.snapshot.cycle,
                              "checkpoint": self.controller.checkpoint()}, Provenance.ENGINEERED_MAPPING,
                              idempotency_key=f"cycle:{self.snapshot.cycle}:completed")
            self._transition(State.WAKE_AGAIN, "memory and controller checkpoint saved")
        elif state == State.RECOVER_FROM_FAILURE:
            self.store.append("recovery.completed", {"cycle": self.snapshot.cycle},
                              Provenance.DETERMINISTIC_EXECUTION, actor="watchdog")
            self._transition(State.PREPARE_SLEEP, "recovered into safe sleep")

    def public_state(self) -> dict[str, Any]:
        with self._lock:
            hour = self.snapshot.simulated_minutes // 60
            minute = self.snapshot.simulated_minutes % 60
            solar_intensity = max(0.0, __import__("math").sin(
                __import__("math").pi * (self.snapshot.simulated_minutes - 390) / 720
            )) if 390 <= self.snapshot.simulated_minutes <= 1110 else 0.0
            return {
                **self.snapshot.to_dict(),
                "mode": self.settings.mode,
                "simulated_time": f"{hour:02d}:{minute:02d}",
                "solar_intensity": round(solar_intensity, 4),
                "sleep_hours_remaining": round(self.snapshot.sleep_minutes_remaining / 60, 2),
                "neural": self.latest_neural,
                "scientific_notice": (
                    "The connectome controller supplies simulated action preferences only. "
                    "Language, code, ranking, tests, and comedy are external engineered components."
                ),
            }

    def public_connectome_map(self) -> dict[str, Any]:
        """Return only display-safe topology metadata for the selected subgraph."""
        return {
            "dataset": self.controller.manifest.get("dataset"),
            "source_kind": self.controller.manifest.get("source_kind"),
            "notice": self.controller.manifest.get("notice"),
            "manifest_hash": self.controller.manifest_hash,
            "neurons": self.controller.manifest.get("neurons", []),
            "edges": self.controller.manifest.get("edges", []),
        }
