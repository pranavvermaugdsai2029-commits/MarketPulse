# Contributing

## Team Workflow

1. Keep `main` demo-safe.
2. Work in small branches named by phase and feature, for example `phase-3-graph`.
3. Run `python -m pytest` before merging.
4. Keep CSV schema changes backward-compatible unless the whole team agrees.
5. Do not introduce live-source dependencies into the default path.

## Ownership Split

- Data and schema: CSV validation, sample fixtures, normalization.
- Graph and agents: supervisor, worker outputs, aggregation, logging.
- UI and evaluator UX: Streamlit controls, visibility, final markdown display.
- Reliability and demo: tests, README, HLD, submission artifacts.
