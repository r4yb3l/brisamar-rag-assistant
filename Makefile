.PHONY: up down seed test unit eval samples

up:
	docker compose up --build

down:
	docker compose down

seed:
	python scripts/seed.py --with-failures

test:
	bash scripts/test.sh

unit:
	cd backend && python -m pytest tests/unit -q

eval:
	cd backend && python -m eval.run_eval

samples:
	python scripts/generate_samples.py
