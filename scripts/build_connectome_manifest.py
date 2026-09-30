"""Build an attributed Male CNS subgraph manifest from local Feather files.

Requires the optional packages pandas and pyarrow. This script intentionally
does not download source data. Column names are discovered conservatively and
must be confirmed against the pinned Male CNS v1.0 files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_column(columns: list[str], choices: tuple[str, ...]) -> str:
    lowered = {column.lower(): column for column in columns}
    for choice in choices:
        if choice.lower() in lowered:
            return lowered[choice.lower()]
    raise ValueError(f"Expected one of {choices}; available columns: {columns}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--connectivity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=512)
    parser.add_argument("--min-synapses", type=int, default=5)
    args = parser.parse_args()
    import pandas as pd

    annotations = pd.read_feather(args.annotations)
    connectivity = pd.read_feather(args.connectivity)
    body = find_column(list(annotations.columns), ("body", "bodyId", "body_id"))
    region = find_column(list(annotations.columns), ("super_class", "class", "cell_class"))
    pre = find_column(list(connectivity.columns), ("body_pre", "bodyId_pre", "bodyIdPre"))
    post = find_column(list(connectivity.columns), ("body_post", "bodyId_post", "bodyIdPost"))
    weight = find_column(list(connectivity.columns), ("weight", "count", "syn_count"))

    seeds = annotations[annotations[region].astype(str).str.contains(
        "dopamin|mushroom|central complex|descending", case=False, na=False
    )].head(args.limit)
    selected = set(int(value) for value in seeds[body])
    edges = connectivity[
        connectivity[pre].isin(selected) & connectivity[post].isin(selected) &
        (connectivity[weight] >= args.min_synapses)
    ].copy()
    connected = set(int(v) for v in edges[pre]) | set(int(v) for v in edges[post])
    nodes = annotations[annotations[body].isin(connected)].head(args.limit)
    ids = [int(v) for v in nodes[body]]
    index = {value: i for i, value in enumerate(ids)}
    manifest_edges = [
        {"source": index[int(row[pre])], "target": index[int(row[post])],
         "weight": float(__import__("math").log1p(row[weight]))}
        for _, row in edges.iterrows() if int(row[pre]) in index and int(row[post]) in index
    ]
    manifest = {
        "dataset": "male-cns:v1.0", "source_kind": "male-cns-derived", "license": "CC-BY 4.0",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source_hashes": {"annotations": sha256(args.annotations), "connectivity": sha256(args.connectivity)},
        "selection_algorithm": "annotated seeds; induced strong-edge subgraph; v0.1",
        "selection_parameters": {"limit": args.limit, "min_synapses": args.min_synapses},
        "neurons": [{"body_id": str(row[body]), "region": str(row[region])} for _, row in nodes.iterrows()],
        "edges": manifest_edges,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

