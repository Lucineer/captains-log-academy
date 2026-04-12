.PHONY: test lint format clean

PYTHON := python3
PIP := pip3

# ── Install ───────────────────────────────────────────────────────

install:
	$(PIP) install -q httpx pytest pytest-asyncio

# ── Test ──────────────────────────────────────────────────────────

test: install
	$(PYTHON) -m pytest tests/ -v --tb=short

test-coverage: install
	$(PYTHON) -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

# ── Lint ──────────────────────────────────────────────────────────

lint:
	$(PYTHON) -m py_compile src/log_pipeline.py
	$(PYTHON) -m py_compile src/log_validator.py
	$(PYTHON) -m py_compile src/log_reader.py
	@echo "All files compile cleanly."

# ── Validate Examples ─────────────────────────────────────────────

validate-examples: install
	@echo "Validating example logs..."
	@for f in examples/*.md; do \
		echo "  Checking $$f..."; \
		$(PYTHON) -c "from pathlib import Path; from src.log_reader import parse_log_file; e = parse_log_file('$$f'); assert e is not None, 'Failed to parse'; assert e.score is not None, 'Missing score'; assert e.score >= 5.0, f'Score {e.score} below threshold'; print(f'    ✓ {e.title} ({e.score}/10)')"; \
	done
	@echo "All examples validated."

# ── Clean ─────────────────────────────────────────────────────────

clean:
	find . -name __pycache__ -delete
	find . -name '*.pyc' -delete
	find . -name '.pytest_cache' -delete
	find . -name '.coverage' -delete
