# Scientific boundaries

InternFly uses a sparse recurrent controller inspired by, and optionally built
from, a selected Male CNS v1.0 connectivity subgraph. It does not claim that a
static connectome can understand language, solve programming problems, browse
the web, or apply for work.

## Provenance classes

- `BIOLOGICAL_CONNECTIVITY`: immutable imported IDs, annotations, transmitter
  predictions, and connection counts.
- `SIMULATED_DYNAMICS`: engineered numerical activity over a graph.
- `ENGINEERED_MAPPING`: mappings between application state and controller I/O.
- `LLM_GENERATED`: external model text or code.
- `DETERMINISTIC_EXECUTION`: state transitions, tests, scores, and policy.
- `FICTIONAL_ENTERTAINMENT`: personality variables, jokes, and dreams.

The development manifest is synthetic and says so in both data and UI. A real
manifest may only use `source_kind: male-cns-derived` when the importer has read
official source files and recorded their hashes.

Plasticity changes a bounded product-owned overlay. It never rewrites or claims
to improve the biological connectome.

