# Pipeline Orchestration for Hydro-Dataset

PYTHON = python3
SRC_DIR = ../src

.PHONY: help extract-all extract-smhi extract-mesan extract-fmi extract-syke build-dataset clean

help:
	@echo "Hydro-Dataset Pipeline Commands:"
	@echo "  make extract-all     - Run all data extraction scripts"
	@echo "  make extract-smhi    - Download SMHI data"
	@echo "  make extract-mesan   - Download MESAN data"
	@echo "  make extract-fmi     - Download FMI data"
	@echo "  make extract-syke    - Download Syke data"
	@echo "  make build-dataset   - Run processing and derivation (Phase 1)"
	@echo "  make clean           - Remove interim and processed data"

extract-all: extract-smhi extract-mesan extract-fmi extract-syke

extract-smhi:
	$(PYTHON) $(SRC_DIR)/extraction/fetch_smhi.py

extract-mesan:
	$(PYTHON) $(SRC_DIR)/extraction/fetch_mesan.py

extract-fmi:
	$(PYTHON) $(SRC_DIR)/extraction/fetch_fmi.py

extract-syke:
	$(PYTHON) $(SRC_DIR)/extraction/fetch_syke.py

build-dataset:
	@echo "Building dataset... (Add processing/derivation scripts here)"
	# Example: $(PYTHON) $(SRC_DIR)/processing/clean_all.py
	# Example: $(PYTHON) $(SRC_DIR)/derivation/derive_swe.py

clean:
	rm -rf ../data/interim/*
	rm -rf ../data/processed/*
