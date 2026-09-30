from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ACTIONS = ["SOLVE_DSA", "COFFEE_BREAK", "SEARCH_JOBS", "REFLECT", "PREPARE_SLEEP"]
OBSERVATIONS = ["energy", "stress", "confidence", "curiosity", "dopamine", "sleep_debt", "caffeine_level"]


@dataclass
class ControllerStep:
    action_scores: dict[str, float]
    selected_preference: str
    active_neurons: int
    mean_activity: float
    peak_activity: float
    region_activity: dict[str, float]
    caffeine_input_gain: float
    caffeine_noise_amplitude: float
    saturation_warning: bool
    provenance_notice: str


class SparseRateController:
    """Engineered rate dynamics over a frozen sparse topology.

    The topology fixture is synthetic unless manifest.source_kind is
    ``male-cns-derived``. This class never presents its activity as biological
    recording or language reasoning.
    """

    def __init__(self, manifest_path: str | Path) -> None:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        self.manifest = manifest
        self.n = len(manifest["neurons"])
        self.regions = [node["region"] for node in manifest["neurons"]]
        self.edges = [(e["source"], e["target"], float(e["weight"])) for e in manifest["edges"]]
        self.activity = [0.0] * self.n
        self.plastic = [0.0] * len(self.edges)
        digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        self.manifest_hash = digest
        seed = int(digest[:16], 16)
        rng = random.Random(seed)
        self.input_map = [[rng.uniform(-0.18, 0.18) for _ in OBSERVATIONS] for _ in range(self.n)]
        self.readout = {action: [rng.uniform(-0.3, 0.3) for _ in range(self.n)] for action in ACTIONS}

    def step(self, observation: dict[str, float], seed: int) -> ControllerStep:
        rng = random.Random(seed)
        recurrent = [0.0] * self.n
        for index, (source, target, weight) in enumerate(self.edges):
            recurrent[target] += (weight + self.plastic[index]) * self.activity[source]
        obs = [float(observation.get(key, 0.0)) / 100.0 for key in OBSERVATIONS]
        caffeine = max(0.0, min(1.0, observation.get("caffeine_level", 0.0) / 100.0))
        caffeine_input_gain = 1.0 + 0.45 * caffeine
        caffeine_noise_amplitude = 0.01 + 0.015 * caffeine
        next_activity = []
        for i in range(self.n):
            external = sum(self.input_map[i][j] * obs[j] for j in range(len(obs))) * caffeine_input_gain
            value = (
                0.72 * self.activity[i]
                + (0.18 + 0.04 * caffeine) * recurrent[i]
                + external
                + rng.uniform(-caffeine_noise_amplitude, caffeine_noise_amplitude)
            )
            next_activity.append(math.tanh(value))
        self.activity = next_activity
        scores = {
            action: sum(weights[i] * self.activity[i] for i in range(self.n)) / max(1, self.n)
            for action, weights in self.readout.items()
        }
        scores["PREPARE_SLEEP"] += max(0.0, (observation.get("sleep_debt", 0) - 55) / 80)
        scores["SOLVE_DSA"] += observation.get("curiosity", 0) / 500
        scores["SEARCH_JOBS"] += observation.get("confidence", 0) / 650
        scores["COFFEE_BREAK"] += max(0.0, (55 - observation.get("caffeine_level", 0)) / 500)
        region_totals: dict[str, list[float]] = {}
        for region, value in zip(self.regions, self.activity, strict=True):
            region_totals.setdefault(region, []).append(abs(value))
        region_activity = {key: sum(values) / len(values) for key, values in region_totals.items()}
        peak = max(abs(x) for x in self.activity)
        active = sum(abs(x) >= 0.2 for x in self.activity)
        return ControllerStep(
            action_scores={key: round(value, 5) for key, value in scores.items()},
            selected_preference=max(scores, key=scores.get),
            active_neurons=active,
            mean_activity=sum(abs(x) for x in self.activity) / self.n,
            peak_activity=peak,
            region_activity=region_activity,
            caffeine_input_gain=caffeine_input_gain,
            caffeine_noise_amplitude=caffeine_noise_amplitude,
            saturation_warning=sum(abs(x) > 0.98 for x in self.activity) > self.n * 0.1,
            provenance_notice=(
                "Simulated dynamics over a Male CNS-derived subgraph; mappings are engineered."
                if self.manifest.get("source_kind") == "male-cns-derived"
                else "Simulated dynamics over a synthetic development fixture; not biological connectivity."
            ),
        )

    def apply_sleep_update(self, reward: float) -> dict[str, float | int | bool]:
        before = sum(abs(x) for x in self.plastic)
        changed = 0
        for index, (source, target, _) in enumerate(self.edges):
            delta = 0.002 * reward * self.activity[source] * self.activity[target]
            updated = max(-0.05, min(0.05, self.plastic[index] * 0.98 + delta))
            changed += int(abs(updated - self.plastic[index]) > 1e-9)
            self.plastic[index] = updated
        after = sum(abs(x) for x in self.plastic)
        stable = all(math.isfinite(x) and abs(x) <= 0.05 for x in self.plastic)
        if not stable:
            self.plastic = [0.0] * len(self.edges)
        return {"changed_edges": changed, "l1_before": before, "l1_after": after, "stable": stable}

    def checkpoint(self) -> dict[str, Any]:
        return {
            "manifest_hash": self.manifest_hash,
            "activity": self.activity,
            "plastic": self.plastic,
            "source_kind": self.manifest.get("source_kind"),
        }
