# Pipeline Orchestration for Hydro-Dataset

PYTHON = python3
SRC_DIR = ../src

.PHONY: help extract-all extract-smhi extract-mesan extract-fmi extract-syke extract-hydobs build-dataset pilot-netcdf swe-grid validate-swe nordic-netcdf clean

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

pilot-netcdf:
	$(PYTHON) $(SRC_DIR)/extraction/fetch_smhi.py
	$(PYTHON) ../scripts/build_pilot_netcdf.py

build-dataset: pilot-netcdf
	@echo "M3 pilot NetCDF complete: data/processed/pilot/dalarna_tier0_2023_2024.nc"

swe-grid:
	$(PYTHON) ../scripts/build_swe_grid.py

validate-swe:
	$(PYTHON) ../scripts/validate_swe_era5.py

extract-hydobs:
	$(PYTHON) $(SRC_DIR)/extraction/fetch_smhi_hydobs.py

nordic-netcdf:
	$(PYTHON) ../scripts/build_nordic_netcdf.py

clean:
	rm -rf ../data/interim/*
	rm -rf ../data/processed/*
