PYTHON ?= python

.PHONY: test prepare reproduce notebooks
test:
	$(PYTHON) -m pytest -q
prepare:
	$(PYTHON) scripts/reproduce/reproduce_all.py --prepare-only
reproduce:
	$(PYTHON) scripts/reproduce/reproduce_all.py
notebooks:
	$(PYTHON) -m jupyterlab notebooks
