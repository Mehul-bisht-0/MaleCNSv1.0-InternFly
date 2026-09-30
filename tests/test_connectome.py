from pathlib import Path

from internfly.connectome import SparseRateController


MANIFEST = Path(__file__).parents[1] / "data/connectome/manifests/dev-subgraph.json"


def test_controller_is_deterministic_for_same_start_and_seed():
    first = SparseRateController(MANIFEST)
    second = SparseRateController(MANIFEST)
    observation = {"energy": 50, "stress": 20, "confidence": 40, "curiosity": 70, "dopamine": 50, "sleep_debt": 10}
    assert first.step(observation, 42) == second.step(observation, 42)


def test_plasticity_is_bounded():
    controller = SparseRateController(MANIFEST)
    controller.step({"energy": 100, "stress": 100, "confidence": 100, "curiosity": 100, "dopamine": 100, "sleep_debt": 100}, 1)
    for _ in range(1000):
        report = controller.apply_sleep_update(1.0)
    assert report["stable"] is True
    assert max(abs(value) for value in controller.plastic) <= 0.05


def test_caffeine_effect_is_explicit_and_bounded():
    controller = SparseRateController(MANIFEST)
    step = controller.step({"caffeine_level": 100}, 7)
    assert step.caffeine_input_gain == 1.45
    assert step.caffeine_noise_amplitude == 0.025
