.PHONY: help setup run desktop lint format check

help:
	@echo "Available targets:"
	@echo "  setup   - create venv and install backend deps"
	@echo "  run     - run Flask app locally"
	@echo "  desktop - run Electron desktop shell"
	@echo "  lint    - run ruff checks"
	@echo "  format  - run black + ruff format"
	@echo "  check   - run lint + syntax compile"

setup:
	python -m venv .venv
	. .venv/Scripts/activate && pip install -r requirements.txt

run:
	python app.py

desktop:
	cd electron && npm run start

lint:
	ruff check src app.py

format:
	black src app.py
	ruff check --fix src app.py

check:
	ruff check src app.py
	python -m compileall src app.py
