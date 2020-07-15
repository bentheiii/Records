.DEFAULT_GOAL := all
isort = python3 -m isort -rc app tests
black = python3 -m black -S -l 120 --target-version py38 app tests

.PHONY: lint
lint:
	python3 -m flake8 app/ tests/
	$(isort) --check-only
	$(black) --check
.PHONY: mypy
mypy:
	python3 -m mypy app

.PHONY: test
test:
	pytest -x --cov=app

.PHONY: testcov
testcov: test
	@echo "building coverage html"
	@coverage html


.PHONY: all
all: lint mypy testcov

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