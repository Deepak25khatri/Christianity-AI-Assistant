.PHONY: up down ingest evals test logs rebuild

up:
	docker compose up -d --build

down:
	docker compose down

ingest:
	docker compose --profile ingest run --rm ingest

evals:
	docker compose --profile evals run --rm evals
	@echo "Scorecard written to server/evals/last_scorecard.md (and .jsonl)"

test:
	cd server && pytest -q

logs:
	docker compose logs -f backend

rebuild:
	docker compose build --no-cache
