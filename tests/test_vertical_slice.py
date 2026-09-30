from dataclasses import replace

from internfly.config import Settings
from internfly.domain import State
from internfly.orchestrator import Orchestrator
from internfly.store import EventStore


def test_one_cycle_always_reaches_sleep_checkpoint(tmp_path):
    store = EventStore(str(tmp_path / "cycle.db"))
    settings = Settings(database_path=str(tmp_path / "cycle.db"), auto_start=False, step_seconds=0, max_cycle_steps=18)
    engine = Orchestrator(store, settings)
    seen = []
    sleep_ticks = 0
    for _ in range(120):
        seen.append(engine.snapshot.state)
        if engine.snapshot.state in {State.SLEEP, State.DREAM, State.CONSOLIDATE_MEMORY}:
            sleep_ticks += 1
        engine.tick()
        if engine.snapshot.state == State.WAKE_AGAIN:
            break
    assert State.SLEEP in seen
    assert State.COFFEE_BREAK in seen
    assert engine.snapshot.state == State.WAKE_AGAIN
    assert sleep_ticks * settings.simulated_minutes_per_tick == 300
    assert seen.count(State.SOLVE_DSA) >= settings.dsa_solve_ticks
    assert seen.count(State.SEARCH_JOBS) >= settings.job_search_ticks
    assert engine.snapshot.coffee_cups == 2
    assert store.query("SELECT COUNT(*) AS count FROM events WHERE event_type='agent.coffee_consumed'")[0]["count"] == 1
    assert store.counts()["cycles_completed"] == 1
    assert store.counts()["dsa_solved"] == 1
