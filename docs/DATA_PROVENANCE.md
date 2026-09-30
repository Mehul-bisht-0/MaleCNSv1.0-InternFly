# Data provenance

## Male CNS

- Dataset: Male CNS v1.0 (`male-cns:v1.0`)
- Publisher: FlyEM / HHMI Janelia and collaborators
- License: CC-BY 4.0
- Project: https://male-cns.janelia.org/
- Downloads: https://male-cns.janelia.org/download/

InternFly needs only the curated neuron annotations, aggregate neurotransmitter
predictions, and segment-to-segment connection-weight table. It does not need EM
volumes, segmentation volumes, skeletons, or individual synapse-point tables.

The project deliberately does not redistribute source data. Generated manifests
include a content SHA-256, selection parameters, retrieval date, exact body IDs,
dominant neuropil, transmitter annotation, edge synapse counts, and attribution.

### Secure neuPrint import

InternFly never accepts a token in source code, command arguments, UI state, or
the event log. Revoke any token pasted into chat or a screenshot, create a new
one, and expose it to the importer only through the local process environment:

```powershell
$env:UV_CACHE_DIR = "$PWD/.uv-cache"
uv sync --extra connectome
$env:NEUPRINT_TOKEN = Read-Host "Paste your rotated neuPrint token" -MaskInput
uv run --extra connectome python scripts/fetch_malecns_subgraph.py --seed-types DNge104 --limit 512
Remove-Item Env:NEUPRINT_TOKEN
```

The generated `data/generated/malecns-subgraph.json` is automatically preferred
on the next API restart. The token is neither printed nor written. The dashboard
will show `male-cns:v1.0` and `male-cns-derived` only when this attributed
manifest is active; otherwise it clearly reports a synthetic development fixture.

The network layout is an engineered anatomical orientation view grouped by
dominant neuropil and broader visual segment. It is not a morphology or EM-volume
rendering. Network firing is simulated activity, never measured fly activity.

## Demo content

DSA questions and fictional job fixtures are project-authored. Companies,
people, roles, applications, and outcomes in demo mode are fictional.
