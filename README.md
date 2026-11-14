# BHnMISnTRA: Radar Evidence & Surface Change Intelligence Platform

> **NASA Space Apps Challenge 2026** — *Dancing with the SARs*  
> **Module**: Member 1 — Data & Scientific Intelligence  
> **Status**: Scientific Processing Pipeline & Beat Test Active | **56 / 56 Acceptance Tests Passing**

---

## 1. Overview

**BHnMISnTRA** (*Bhoomi Nireekshanam & Multi-temporal SAR Intelligence for Surface Change Tracking & Resilience Analysis*) is a high-assurance radar remote sensing and evidence validation platform. It processes multi-temporal Synthetic Aperture Radar (SAR) backscatter time-series from **Sentinel-1** and **NISAR** to detect, verify, and track surface changes (such as flood inundation, canopy clearing, and landslides) while strictly preventing false positives from speckle noise, imaging geometry distortions, and environmental confounders.

This repository hosts **Member 1 (Data & Scientific Intelligence)**, which provides the mathematical, physical, and scientific foundation for the platform.

---

## 2. Scientific Core Architecture

```
                                  [ SAR Granules (Sentinel-1 / NISAR) ]
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │    1. Strict Ingestion &      │
                                    │     Geometry Verification     │
                                    └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │  2. Radiometric Calibration   │
                                    │      (RAW_DN / Linear / dB)   │
                                    └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │ 3. Linear-Space Speckle Filter│
                                    │    (Log-bias prevention)      │
                                    └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │   4. Log-Ratio Change &       │
                                    │      Spatial Tuning Split     │
                                    └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │ 5. Morphological Sieving(MMU) │
                                    └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │  6. Multi-Temporal Beat Test  │
                                    │     (N >= 3 subsequent passes)│
                                    └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │  7. Confounder Assessment &   │
                                    │      Evidence Ledger Payload  │
                                    └───────────────────────────────┘
```

### Key Scientific Principles:

1. **Product-Aware Radiometric Calibration & Double-Calibration Guards**:
   - Explicit discriminated unions for `RAW_DN` ($10 \log_{10}(\text{DN}^2)$), `CALIBRATED_LINEAR_POWER` ($10 \log_{10}(\text{linear} \times k)$), and `CALIBRATED_DB` (pass-through).
   - Rejects negative values declared as linear power or raw DN to prevent double-calibration.
2. **Logarithmic Bias Prevention**:
   - Speckle filtering (Boxcar / Lee) applied directly to decibel (dB) rasters produces a severe downward bias ($\sim 2.5\text{ dB}$) because $\mathbb{E}[\log(X)] \ne \log(\mathbb{E}[X])$.
   - The pipeline strictly converts $\text{dB} \to \text{Linear Power}$, applies spatial filtering, and transforms back to dB.
3. **Data-Snooping Prevention**:
   - Threshold computation (Fixed dB, Robust MAD, Otsu) is strictly partitioned onto an isolated spatial tuning split, preventing circular threshold overfitting on evaluation regions.
4. **Pre-Registered Multi-Temporal Beat Test**:
   - Requires $\ge 3$ subsequent acquisitions ($N \ge 3$).
   - For flood recession: enforces monotonic drainage with a 5% measurement noise cushion and explicitly detects zero-area re-inundation surges.
   - For sustained change: enforces exact integer cross-multiplication ($3 \times \text{re-detections} \ge 2 \times \text{observations}$).
5. **Three-State Evidence Classification**:
   - `Supported`: Verified geometry, Beat Test passed, zero unresolved critical confounders, zero scientific uncertainty.
   - `Inconclusive`: Scientific discrepancy, re-inundation failure, unresolved critical confounder, or administrative override.
   - `Unverified`: Fewer than 3 subsequent acquisitions or unassessed baseline.
   - *Administrative exemptions explain workflow adherence; they never manufacture physical evidence.*
6. **No Artificial Percentages**:
   - Rejects synthetic "confidence scores" (e.g. 98.4%) in favor of deterministic physical invariants and full audit provenance in the inspectable **Evidence Ledger**.

---

## 3. Directory Layout

```
.
├── .brain/                         # Cross-session persistent memory & PRD architecture
│   ├── DECISIONS.md                # Architectural decision records
│   ├── HANDOFF.md                  # Inter-module contracts & handoff specification
│   ├── MAP.md                      # Codebase structure & component index
│   └── STATUS.md                   # Real-time implementation status & test metrics
├── src/
│   └── bhnmisntra_science/         # Core scientific module (Member 1)
│       ├── __init__.py             # Public module exports
│       ├── constants.py            # PRD constants (frozen runtime values)
│       ├── enums.py                # Type-safe scientific domain enums
│       ├── exceptions.py           # Domain exceptions
│       ├── types.py                # UTC normalizers & strict validators
│       ├── config.py               # Pydantic v2 metadata & parameter schemas
│       ├── policies.py             # Incidence angle, confounder, & classifier policies
│       ├── pipeline.py             # End-to-end scientific pipeline orchestrator
│       ├── processing/             # SAR signal processing algorithms
│       │   ├── __init__.py
│       │   ├── calibration.py      # Radiometric calibration & double-calibration guard
│       │   ├── alignment.py        # Spatial grid & affine geotransform verification
│       │   ├── speckle.py          # Boxcar & Lee filters with log-bias prevention
│       │   └── log_ratio.py        # Log-ratio differencing, tuning split, thresholding & sieving
│       └── beat_test/              # Multi-temporal trajectory verification
│           ├── __init__.py
│           └── tracker.py          # Connected component tracking & re-inundation detection
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Synthetic SAR fixtures (labeled Tier 3)
│   ├── run_tests.py                # Test runner
│   ├── test_stage1_contracts.py    # 31 contract & schema invariants tests
│   ├── test_processing.py          # 22 signal processing & Beat Test tests
│   └── test_pipeline_e2e.py        # 3 full-stack end-to-end pipeline tests
├── BHnMISnTRA_PRD.pdf              # Authoritative PRD specification
├── GEMINI.md                       # Antigravity Pro master agentic operating prompt
├── .gitignore                      # Python & cache exclusion rules
└── README.md                       # Project documentation
```

---

## 4. Running the Test Suite

The module runs under standard Python (3.10+) with `numpy`, `scipy`, and `pydantic`.

```bash
# Run the complete test suite (56 acceptance tests)
python tests/run_tests.py
```

### Test Suite Summary:
- `test_stage1_contracts.py`: 31 tests (Antimeridian bounding boxes, UTC microsecond serialization, strict non-boolean ints, discriminated unions, geometry compatibility, confounder decision matrix).
- `test_processing.py`: 22 tests (Radiometric calibration states, double-calibration prevention, co-registration geotransforms, speckle filter log-bias prevention, Robust MAD, Otsu thresholding, morphological MMU sieving, Beat Test tracking).
- `test_pipeline_e2e.py`: 3 tests (End-to-end multi-temporal flood recession to `SUPPORTED`, re-inundation surge detection to `INCONCLUSIVE`, critical confounder flagging to `INCONCLUSIVE`, Evidence Ledger JSON generation).

**Total: 56 tests passing in 0.02s.**

---

## 5. Team Integration Specifications

Member 1 exports the following contracts for platform integration:
- **Member 2 (FastAPI Backend)**: `run_scientific_pipeline(config: InvestigationConfig, raster_data: dict) -> PipelineExecutionResult`
- **Member 3 (MapLibre UI)**: `result.sieved_change_mask`, `result.diff_raster_db`, `result.evidence_ledger` (GeoJSON and JSON audit payload)
- **Member 4 (Evaluation Lead)**: Output arrays, confusion matrix inputs, and threshold tuning evaluation rasters.

