# <p align="center">❄️ Hydro-Dataset: Nordic Regional Hydrology ❄️</p>

<p align="center">
  <strong>Multi-Modal Data Fusion for Snow, Water, and Environmental Research</strong>
</p>

<p align="center">
  <a href="https://github.com/getnetdemil/Hydro-Dataset/actions"><img src="https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge&logo=github-actions" alt="Build Status"></a>
  <a href="https://github.com/getnetdemil/Hydro-Dataset/wiki"><img src="https://img.shields.io/badge/Docs-Wiki-blue?style=for-the-badge&logo=wikipedia" alt="Documentation"></a>
  <a href="https://hydroimaging.github.io/"><img src="https://img.shields.io/badge/Workshop-HydroImaging_2026-orange?style=for-the-badge" alt="Workshop"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"></a>
</p>

---

## 🌊 Overview

The **Hydro-Dataset** is a modular, script-driven pipeline designed to create a comprehensive, research-grade dataset for the Nordic region. By fusing **imaging data** (satellite and reanalysis) with **in-situ observations**, we provide high-fidelity benchmarks for:

*   🏔️ **Snow Hydrology**: Downscaled Snow Water Equivalent (SWE) models.
*   💧 **Water Resources**: Catchment-scale discharge and runoff potential.
*   🌿 **Water Quality**: Spatio-temporal nutrient and turbidity monitoring.

Developed for the **[Workshop on Mining Imaging Data for Hydrological and Environmental Modelling (HydroImaging 2026)](https://hydroimaging.github.io/)**, this project bridges the gap between Earth Observation (EO) and physical environmental modelling.

---

## 🛰️ Phase 1 Data Ecosystem

We harmonize heterogeneous data streams from four major Nordic providers:

| Provider | Origin | Type | Primary Variables |
| :--- | :--- | :--- | :--- |
| **🇸🇪 SMHI** | Sweden | Station | Temp, Precip, Snow Depth, Water Level |
| **🧩 MESAN** | Sweden | Reanalysis | 2.5km Meteorological Grids (Imaging) |
| **🇫🇮 FMI** | Finland | Station/EO | Satellite Snow Cover, Soil Moisture |
| **🌊 Syke** | Finland | Hydrological | Discharge (Q), Nutrients (N, P), Turbidity |

---

## 🏗️ Project Architecture

The codebase follows a strictly modular, "Pipeline-First" philosophy:

```text
Hydro-Dataset/
├── data/                 # 📂 Multi-tier storage (Raw ➔ Interim ➔ Processed)
├── docs/                 # 📖 Deep documentation and Project Wiki
├── notebooks/            # 🧪 EDA and Research Prototyping
├── pipelines/            # ⚙️ Orchestration layer (Makefile-driven)
├── src/                  # 💻 Modular Python Logic
│   ├── common/           # Shared utilities (Geo-utils, Config, IO)
│   ├── extraction/       # Provider-specific API downloaders
│   ├── processing/       # Spatial alignment & QC cleaning
│   └── derivation/       # Research-grade parameter logic (SWE, Runoff)
├── tests/                # 🚦 Automated Validation Suite
└── .env.example          # 🔑 Environment Template
```

---

## 🚀 Getting Started

### 1. Environment Setup
Clone the repository and initialize your Python environment:
```bash
git clone https://github.com/getnetdemil/Hydro-Dataset.git
cd Hydro-Dataset
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration
Create your local environment file and adjust the data directories:
```bash
cp .env.example .env
# Edit .env with your local paths and API keys
```

### 3. Execution
Run the end-to-end pipeline using the provided Makefile:
```bash
cd pipelines
make extract-all     # Ingest raw data from all providers
make build-dataset   # Harmonize, process, and derive parameters
```

---

## 📊 Foundation Model Ready

This project is a pioneer in creating **Foundation-Model-Ready** environmental benchmarks. We provide:
*   ✅ **Clean, Aligned Cubes**: Xarray-compatible NetCDF files ready for LLM/VLM training.
*   ✅ **Metadata Compliance**: Full adherence to CF (Climate and Forecast) conventions.
*   ✅ **Image-Text Pairs**: Curated datasets for training Vision-Language Models.

---

## 📖 Documentation & Research

Explore our extensive internal documentation for deep dives into our methodology:

*   📘 **[Project Wiki](https://github.com/getnetdemil/Hydro-Dataset/wiki)** - The "Big Picture" knowledge base.
*   📐 **[System Architecture](docs/ARCHITECTURE.md)** - Logic and data flow details.
*   🛰️ **[Data Source Registry](docs/DATA_SOURCES.md)** - API specs and variables.
*   🧪 **[Derivation Methods](docs/DERIVATION_METHODS.md)** - Formulas and ML models.
*   🤝 **[Contributing Rules](docs/CONTRIBUTING.md)** - Guide for researchers.

---

## 📅 Roadmap to HydroImaging 2026

- [x] **Project Scaffolding** (Alpha Release)
- [x] **M1–M2: Extraction & Harmonization** (SMHI, FMI, Syke, MESAN; LAEA reprojection)
- [x] **M3: Dalarna Pilot** — `dalarna_tier0_2023_2024.nc` (22 stations, CF-1.9)
- [x] **M4: SWE Derivation & Validation** — Sturm (2010) + Kriging + ERA5-Land (R=0.78)
- [x] **M6: Nordic Dataset v1.0** — `nordic_tier0_2015_2024.nc` (582 stations, 9 seasons)
- [ ] **M5: Water Quality Proxy** (FMI turbidity + Syke nutrients)
- [ ] **M7: Benchmarking** (RMSE/KGE vs field gold standards)
- [ ] **M8: Visual Analytics** (spatial maps + time-series figures)
- [ ] **M9: Submission** (May 13, 2026)

---

<p align="center">
  <i>"Harnessing the power of multi-sensor data to model the Nordic water cycle."</i>
</p>

<p align="center">
  <img src="https://img.shields.io/github/issues/getnetdemil/Hydro-Dataset?style=flat-square" alt="Issues">
  <img src="https://img.shields.io/github/stars/getnetdemil/Hydro-Dataset?style=flat-square" alt="Stars">
  <img src="https://img.shields.io/github/forks/getnetdemil/Hydro-Dataset?style=flat-square" alt="Forks">
</p>
