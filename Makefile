.DEFAULT_GOAL := all
isort = python -m isort -l 120 records tests

.PHONY: format
format:
	$(isort)

.PHONY: lint
lint:
	python -m flake8 records/ tests/
	$(isort) --check-only

.PHONY: test
test:
	python -m pytest tests/unittests/ -x --cov=records --cov-report term-missing --no-cov-on-fail --cov-branch


.PHONY: all
all: format lint test

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf dist