.PHONY: up down ingest evals logs rebuild

up:
	docker compose up -d --build

down:
	docker compose down

ingest:
	docker compose --profile ingest run --rm ingest

evals:
	docker compose --profile evals run --rm evals
	@echo "Scorecard at sqlite_data volume:/data/scorecard.md (and .jsonl)"

logs:
	docker compose logs -f backend

rebuild:
	docker compose build --no-cache
