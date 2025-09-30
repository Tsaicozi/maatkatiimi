.PHONY: setup run run-idea fmt clean test setup-env3

setup:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip
	pip install -r requirements.txt || true

setup-env3:
	cp .env.example .env3
	@echo "Muokkaa .env3 tiedostoa ja lisää API-avaimet"

run:
	python run.py "feature: lisää kirjautumissivu"

run-idea:
	python run_idea.py "brief: EU data center REITit hyötyvät AI‑kysynnästä 2025–2027"

fmt:
	ruff check . --fix || true

clean:
	rm -rf .venv __pycache__ .memory

test:
	python -m pytest tests/ || echo "Testit tulossa myöhemmin"