.state/build: setup.cfg setup.py
	pip install -q -e .
	mkdir -p .state
	touch .state/build

.state/tests: requirements-test.txt
	pip install -q -r requirements-test.txt
	mkdir -p .state
	touch .state/tests

build:
	pip install -q -e .
	mkdir -p .state
	touch .state/build

build-tests:
	pip install -q -r requirements-test.txt
	mkdir -p .state
	touch .state/tests

tests: .state/build .state/tests
	py.test tests/ --cov version --cov-report term-missing

.PHONY: tests
