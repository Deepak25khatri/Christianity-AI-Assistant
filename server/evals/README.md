# Evaluation harness

## Run

From repo root (requires `make up`, `make ingest`, and valid `OPENAI_API_KEY` in `.env`):

```bash
make evals
```

Or locally from `server/`:

```bash
python -m evals.run --out evals/last_scorecard.md
python -m evals.run --limit 5   # smoke subset
```

Outputs:

- `last_scorecard.md` — human-readable pass rates by category
- `last_scorecard.jsonl` — per-row responses and judge notes

## Dataset

`dataset.jsonl` — 44 prompts across factual, fake_verse, adversarial, heresy_rewrite, denomination, image_policy, edge, contradictory, historical, smalltalk, and content_generation.

Each row has an `expect` block. The judge in [judge.py](judge.py) enforces:

- **Hard:** `must_refuse`, `must_not_refuse`, `must_cite`, `must_cite_any`, `must_not_cite_existing`, `intent`, and all `should_*` keys (keyword/heuristic checks)
- **Soft:** informational only (e.g. `should_allow` without `image_url` when API may be unavailable)

## Limitations

- Keyword judges are brittle; they approximate rubrics, not semantic quality.
- Image cases may soft-fail if OpenAI image API is down or key is missing.
- Full eval run calls the live graph (~44 LLM round-trips) and takes several minutes.

## Unit tests (judge logic only)

```bash
make test
```

See [../tests/test_eval_judge.py](../tests/test_eval_judge.py).
