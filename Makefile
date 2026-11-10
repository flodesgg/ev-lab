.PHONY: check check-all lint typecheck test test-all fmt cpp

# fast set: must stay under a minute
check: lint typecheck test

# everything, including @pytest.mark.slow
check-all: lint typecheck test-all

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

typecheck:
	uv run mypy

test:
	uv run pytest

test-all:
	uv run pytest -m "slow or not slow"

fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests

# the C++ hand evaluator (also built on demand by the tests and by `ev cards-cpp`)
cpp:
	mkdir -p build
	c++ -O2 -std=c++17 -Wall -Wextra -Wpedantic -Werror -o build/ev_eval cpp/main.cpp
