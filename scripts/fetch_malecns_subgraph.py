"""Fetch a real, attributed Male CNS v1.0 controller subgraph from neuPrint.

The token is read only from NEUPRINT_TOKEN and is never printed or written.
The resulting JSON contains real body IDs, connectivity, annotations, dominant
neuropils and transmitter-derived signs. Engineered dynamics and I/O mappings
remain explicitly separate from this biological connectivity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DATASET = "male-cns:v1.0"
SERVER = "https://neuprint.janelia.org"


def first_present(record: dict[str, Any], names: tuple[str, ...], default: Any = None) -> Any:
    for name in names:
        value = record.get(name)
        if value is not None and str(value) not in {"", "nan", "None"}:
            return value
    return default


def super_segment(roi: str, neuron_class: str) -> str:
    key = (roi + " " + neuron_class).upper()
    groups = (
        ("optic-lobe", ("AME", "ME_", "LO_", "LOP", "OPTIC")),
        ("mushroom-body", ("MB_", "PED", "CA_", "MUSHROOM", "KENYON")),
        ("central-complex", ("EB", "FB", "PB", "NO", "BU_", "CENTRAL COMPLEX")),
        ("olfactory", ("AL_", "LH_", "ANTENNAL", "OLFACT")),
        ("superior-protocerebrum", ("SMP", "SIP", "SLP", "SUPERIOR")),
        ("lateral-complex", ("LAL", "GA_", "CRE", "LATERAL ACCESSORY")),
        ("ventrolateral", ("AVLP", "PVLP", "PLP", "WED", "VENTROLATERAL")),
        ("gnathal", ("GNG", "GNATHAL")),
        ("ventral-nerve-cord", ("VNC", "T1", "T2", "T3", "ABD", "LEG", "WING")),
        ("descending", ("DESCENDING", "DN")),
        ("ascending", ("ASCENDING", "AN")),
    )
    for label, needles in groups:
        if any(needle in key for needle in needles):
            return label
    return "central-brain-other"


def transmitter_sign(value: str) -> tuple[float, str]:
    key = value.lower()
    if "gaba" in key or "glut" in key:
        return -1.0, "inhibitory-model-sign"
    if "acetylch" in key or key in {"ach", "cholinergic"}:
        return 1.0, "excitatory-model-sign"
    if any(name in key for name in ("dopamine", "octopamine", "serotonin", "tyramine")):
        return 0.35, "modulatory-model-sign"
    return 1.0, "unknown-unsigned-default"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/generated/malecns-subgraph.json"))
    parser.add_argument("--seed-types", nargs="+", default=["DNge104"])
    parser.add_argument("--limit", type=int, default=512)
    parser.add_argument("--partners-per-seed", type=int, default=48)
    parser.add_argument("--min-synapses", type=int, default=5)
    parser.add_argument("--max-edges", type=int, default=5000)
    args = parser.parse_args()
    token = os.environ.get("NEUPRINT_TOKEN", "").strip()
    if not token:
        raise SystemExit("NEUPRINT_TOKEN is required. Set it locally; never place it in source control.")

    from neuprint import Client, NeuronCriteria, fetch_adjacencies, fetch_neurons

    client = Client(SERVER, dataset=DATASET, token=token)
    seed_criteria = NeuronCriteria(type=args.seed_types)
    seed_neurons, _ = fetch_neurons(seed_criteria, client=client)
    if seed_neurons.empty:
        raise SystemExit("No seed neurons matched: " + ", ".join(args.seed_types))

    outgoing, _ = fetch_adjacencies(
        seed_criteria,
        None,
        min_total_weight=args.min_synapses,
        client=client,
    )
    incoming, _ = fetch_adjacencies(
        None,
        seed_criteria,
        min_total_weight=args.min_synapses,
        client=client,
    )
    body_pre = "bodyId_pre"
    body_post = "bodyId_post"
    weight_col = "weight"
    for required in (body_pre, body_post, weight_col):
        if required not in outgoing.columns and required not in incoming.columns:
            raise SystemExit("neuPrint adjacency response is missing expected column: " + required)

    combined = __import__("pandas").concat([outgoing, incoming], ignore_index=True)
    combined = combined[combined[weight_col] >= args.min_synapses]
    seed_ids = set(int(value) for value in seed_neurons["bodyId"].tolist())
    selected = set(seed_ids)
    for seed_id in seed_ids:
        local = combined[
            (combined[body_pre] == seed_id) | (combined[body_post] == seed_id)
        ].nlargest(args.partners_per_seed, weight_col)
        selected.update(int(value) for value in local[body_pre].tolist())
        selected.update(int(value) for value in local[body_post].tolist())
    if len(selected) > args.limit:
        partner_strength: dict[int, float] = {value: float("inf") for value in seed_ids}
        for _, row in combined.iterrows():
            for column in (body_pre, body_post):
                body_id = int(row[column])
                partner_strength[body_id] = partner_strength.get(body_id, 0) + float(row[weight_col])
        selected = set(sorted(selected, key=lambda value: partner_strength.get(value, 0), reverse=True)[: args.limit])

    criteria = NeuronCriteria(bodyId=sorted(selected))
    neurons_frame, synapse_distribution = fetch_neurons(criteria, client=client)
    dominant_roi: dict[int, str] = {}
    if not synapse_distribution.empty and {"bodyId", "roi"}.issubset(synapse_distribution.columns):
        distribution = synapse_distribution.copy()
        distribution["total"] = distribution.get("pre", 0) + distribution.get("post", 0)
        dominant_rows = distribution.sort_values("total", ascending=False).drop_duplicates("bodyId")
        dominant_roi = {int(row["bodyId"]): str(row["roi"]) for _, row in dominant_rows.iterrows()}

    records = neurons_frame.to_dict(orient="records")
    records_by_id = {int(record["bodyId"]): record for record in records}
    ordered_ids = [int(record["bodyId"]) for record in records]
    index = {body_id: position for position, body_id in enumerate(ordered_ids)}
    nodes = []
    signs: dict[int, float] = {}
    for body_id in ordered_ids:
        record = records_by_id[body_id]
        roi = dominant_roi.get(body_id, str(first_present(record, ("primaryRoi",), "unknown")))
        neuron_class = str(first_present(record, ("class", "super_class", "cellClass"), "unknown"))
        transmitter = str(first_present(record, ("predictedNt", "ntType", "neurotransmitter"), "unknown"))
        sign, sign_basis = transmitter_sign(transmitter)
        signs[body_id] = sign
        nodes.append({
            "body_id": str(body_id),
            "type": str(first_present(record, ("type", "instance"), "untyped")),
            "class": neuron_class,
            "region": roi,
            "super_segment": super_segment(roi, neuron_class),
            "hemisphere": str(first_present(record, ("somaSide", "rootSide", "side"), "unknown")),
            "transmitter": transmitter,
            "transmitter_sign": sign,
            "sign_basis": sign_basis,
            "biological_source": True,
        })

    induced = combined[
        combined[body_pre].isin(index) & combined[body_post].isin(index)
    ].nlargest(args.max_edges, weight_col)
    if induced.empty:
        raise SystemExit(
            "The selected neurons had no induced edges at the configured synapse threshold. "
            "Try lowering --min-synapses or increasing --partners-per-seed."
        )
    max_log_weight = max(1.0, max(math.log1p(float(value)) for value in induced[weight_col].tolist()))
    edges = []
    for _, row in induced.iterrows():
        source_id = int(row[body_pre])
        target_id = int(row[body_post])
        count = int(row[weight_col])
        edges.append({
            "source": index[source_id],
            "target": index[target_id],
            "synapse_count": count,
            "weight": round(signs.get(source_id, 1.0) * math.log1p(count) / max_log_weight, 7),
        })

    generated_at = datetime.now(UTC).isoformat()
    selection = {
        "seed_types": args.seed_types,
        "limit": args.limit,
        "partners_per_seed": args.partners_per_seed,
        "min_synapses": args.min_synapses,
        "max_edges": args.max_edges,
    }
    manifest = {
        "dataset": DATASET,
        "source_kind": "male-cns-derived",
        "license": "CC-BY 4.0",
        "attribution": "Male CNS v1.0, FlyEM / HHMI Janelia and collaborators",
        "source_url": "https://male-cns.janelia.org/",
        "retrieved_at": generated_at,
        "selection_algorithm": "typed seeds plus strongest incoming/outgoing partners; induced subgraph",
        "selection_parameters": selection,
        "notice": (
            "Real Male CNS v1.0 connectivity. Activity, software inputs, action readouts and "
            "plasticity remain engineered simulation layers."
        ),
        "neurons": nodes,
        "edges": edges,
    }
    payload = json.dumps(manifest, indent=2, sort_keys=True)
    manifest["content_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"Wrote {len(nodes)} real Male CNS neurons and {len(edges)} edges to {args.output}. "
        "The neuPrint token was not stored."
    )


if __name__ == "__main__":
    main()
