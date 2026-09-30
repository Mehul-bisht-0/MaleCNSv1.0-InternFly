# Metrics implemented in v0.1

The event log is authoritative. `/api/metrics` currently projects completed
cycles, DSA attempts/solutions/success rate, jobs discovered/evaluated, drafts
created/pending/approved, memories, dreams, the entertainment-only 10x score,
and estimated flies per engineer.

Percentages are derived from numerator and denominator counts, never averaged
from prior percentages. Future PostgreSQL projections can rebuild from the same
event vocabulary without changing API meanings.

