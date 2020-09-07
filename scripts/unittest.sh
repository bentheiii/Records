# run the unittests with branch coverage
python -m poetry run python -m pytest --cov-branch --cov=./records --cov-report=xml tests/