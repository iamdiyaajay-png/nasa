# BHRAMANASTHRA: Complete Repository Integration Handoff Report
## Module: Member 1 — Data & Scientific Intelligence (Core Radar Evidence & Processing Engine)
### NASA Space Apps Challenge 2026 — *Dancing with the SARs*

**Repository Path**: `c:\Users\Diya\OneDrive\Apps\nasa`  
**Document**: `INTEGRATION_HANDOFF.md`  
**Author**: Lead Data & Scientific Intelligence Specialist (Member 1)  
**Date**: November 2026  
**Status**: Frozen & Validated | **94 / 94 Acceptance Tests Passing (100%)**  

---

## 1. Repository Purpose and Responsibilities

This repository hosts **Member 1 (Data & Scientific Intelligence)** of the **BHRAMANASTHRA** platform (*Radar Evidence & Surface Change Intelligence Platform*).

### Core Responsibilities:
1. **Mathematical & Scientific Kernel**: Encapsulates all physical and radar remote sensing logic for multi-temporal C-band (Sentinel-1) and L-band (NISAR) Synthetic Aperture Radar (SAR) backscatter analysis.
2. **Sentinel-1 Slice Assembly**: Performs direct abutting along-track concatenation of dual-slice acquisitions (North and South scenes) onto master cartographic grids (`EPSG:32643` for UTM Zone 43N) without artificial overlap blending.
3. **Product-Aware Radiometric Calibration**: Enforces strict guards converting raw Digital Numbers ($DN$) or linear power to physical backscatter in decibels ($\sigma^0\text{ dB}$ / $\gamma^0\text{ dB}$), strictly preventing double-calibration.
4. **Logarithmic Bias Prevention**: Converts backscatter from decibels to linear power prior to spatial speckle filtering (Boxcar / Lee), eliminating the $\sim 2.5\text{ dB}$ downward underestimation caused by Jensen's Inequality on logarithmic data ($\mathbb{E}[\log X] \ne \log \mathbb{E}[X]$).
5. **Data-Snooping Prevention**: Enforces spatial tuning split partitioning to ensure change-detection thresholds (Fixed dB, Robust MAD, Otsu) are calculated on isolated tuning subsets rather than evaluation pixels.
6. **Multi-Temporal Beat Test & Four-State Tracking**: Enforces connected-component tracking across repeat satellite overpasses ($N \ge 3$), categorizing inundation dynamics into `PERSISTENT_STAGNATION`, `RECEDING`, `RE_INUNDATED`, and `DRAINED`.
7. **Three-Tier Physical Corroboration Framework**: Evaluates environmental drivers (meteorological precipitation forcing $\ge 50\text{ mm}$, hydraulic plausibility, surface wind calm limits $\le 4.0\text{ m/s}$) to explain secondary inundation surges without false positive flood claims.
8. **Anti-Hallucination Invariant Enforcement**: Enforces PRD Hard Gates (fewer than 3 subsequent acquisitions $N < 3$ strictly forces `EvidenceStatus.UNVERIFIED`; missing observations are never interpreted as drainage).
9. **Cryptographic Evidence Ledger Generation**: Produces immutable, serializable audit ledgers recording all processing parameters, calibration states, coverage ratios, and spatial masks.

---

## 2. Technology Stack and Version Requirements

- **Runtime / Language**: Python **3.10+** (Actively verified on Python **3.11.9** 64-bit on Windows).
- **Core Computational Libraries**:
  - `pydantic` >= 2.0.0 (Strictly utilizes Pydantic v2 schemas, `BaseModel`, discriminated unions, custom serializers, and model validators).
  - `numpy` >= 1.22.0, < 2.0.0 (High-performance 2D/3D float32 multidimensional array operations and matrix indexing).
  - `scipy` >= 1.8.0 (`scipy.ndimage` for morphological sieving, connected-component labeling, binary erosion/dilation, and spatial filtering).
- **Standard Library Modules**: `dataclasses`, `datetime`, `json`, `math`, `re`, `ssl`, `urllib.request`, `urllib.parse`, `typing`, `unittest`.
- **Optional GIS Extensions (for disk-level GeoTIFF I/O)**:
  - `rasterio` >= 1.3.0 or `gdal` >= 3.4.0 (Optional; core pipeline operates purely in-memory via numpy float arrays and affine metadata).
- **Compiler / Native Dependencies**: Zero C-extensions, Cython, or Rust compilation required for Member 1 core logic.

---

## 3. Complete Directory Structure

*(Excluding `.git`, `node_modules`, `__pycache__`, virtual environments, and temporary artifacts)*

```text
c:\Users\Diya\OneDrive\Apps\nasa\
├── .agents/                                      # Swarm agent skills and rules
│   ├── rules/
│   └── skills/                                  # 13 multi-agent capability skills
│       ├── 21st/
│       ├── awesome-design-md/
│       ├── claude-code-setup/
│       ├── claude-image-generation/
│       ├── claude-prompt-meta-harness/
│       ├── headroom/
│       ├── one-skill-to-rule-them-all/
│       ├── playwright-cli/
│       ├── project-brain/
│       ├── strix-pentest/
│       ├── swarm-council/
│       ├── taste-skill/
│       └── web-design-guidelines/
├── .brain/                                       # Persistent cross-session project memory
│   ├── DECISIONS.md                              # Architectural Decision Records (ADR 001 - 004)
│   ├── HANDOFF.md                                # Multi-agent execution context
│   ├── MAP.md                                    # Repository topology & file registry
│   └── STATUS.md                                 # Real-time milestone tracker & test metrics
├── research/                                     # Authoritative scientific audit & specification records
│   ├── ACQUISITION_MANIFEST.md                   # Frozen 7-date Sentinel-1 Track 165 manifest
│   ├── BEAT_TEST_ASSESSMENT.md                   # Multi-temporal Beat Test framework
│   ├── CASE_STUDY_FEASIBILITY_KUTTANAD.md        # Kuttanad delta geodetic & hydraulic baseline
│   ├── FINAL_DECISION_AND_NEXT_ACTIONS.md        # Case study selection & architectural roadmap
│   ├── PHASE_1_1_INDEPENDENT_AUDIT.md            # Stage 1 contract & PRD audit
│   ├── PHASE_1_2_DATA_GATE_READINESS.md          # Satellite archive accessibility assessment
│   ├── PHASE_1_3_IMPLEMENTATION_READINESS.md     # Architecture & engineering readiness audit
│   ├── PHASE_1_4_1_CORRECTION_AUDIT.md           # Parameter reclassification (provisional vs verified)
│   ├── PHASE_1_4_SCIENTIFIC_RULE_VALIDATION.md   # Mathematical rule validation report
│   ├── PHASE_1_5_SCIENTIFIC_SPECIFICATION.md     # Consolidated frozen scientific specification
│   ├── PHASE_2_1_SLICE_ASSEMBLER_REPORT.md       # Direct abutting slice assembler architecture
│   ├── PHASE_2_2_1_INDEPENDENT_AUDIT.md          # Phase 2.2 independent scientific audit
│   ├── PHASE_2_2_TEMPORAL_TRACKER_REPORT.md      # Four-state temporal Beat Test architecture
│   ├── PHASE_2_3_PIPELINE_INTEGRATION_REPORT.md  # End-to-end pipeline integration report
│   ├── PHASE_2_4_1_EVIDENCE_PROVENANCE_AUDIT.md  # Forensic smoke test provenance audit
│   ├── PHASE_2_4_REAL_DATA_SMOKE_TEST.md         # 3-date 6-granule smoke test report
│   ├── PHASE_2_5_NISAR_ARCHIVE_AND_COVERAGE_AUDIT.md # NISAR archive, coverage & auth audit
│   ├── REFERENCE_EVIDENCE_MANIFEST.md            # Optical Sentinel-2 / Landsat reference manifest
│   └── SCIENTIFIC_RISK_REGISTER.md               # Scientific risk register & mitigations
├── scratch/                                      # Forensic query scripts & audit runners
│   ├── check_asf_access.py                       # Live NASA ASF DAAC search probe
│   ├── check_nisar_archive.py                    # NASA CMR & ASF global NISAR query
│   ├── deep_nisar_audit.py                       # Forensic NISAR collection & granule auditor
│   ├── inspect_kuttanad_nisar.py                 # Kuttanad-specific NISAR record inspector
│   ├── probe_errors.py                           # HTTP error body inspector
│   ├── probe_nisar_download.py                   # NISAR download authentication tester
│   └── run_real_data_smoke_test.py               # Pilot integration test harness script
├── src/                                          # Core Scientific Package
│   └── bhnmisntra_science/
│       ├── __init__.py                           # Public library API exports
│       ├── config.py                             # Pydantic v2 schemas, parameters & configs
│       ├── constants.py                          # Frozen PRD constants & mathematical bounds
│       ├── enums.py                              # Strongly-typed domain enums
│       ├── exceptions.py                         # Strict domain typed exception hierarchy
│       ├── pipeline.py                           # End-to-end pipeline orchestrator & Ledger
│       ├── policies.py                           # Incidence angle, confounder, & classifier policies
│       ├── types.py                              # Strict validators, UTC normalizers, immutable base
│       ├── beat_test/                            # Multi-temporal trajectory subpackage
│       │   ├── __init__.py
│       │   └── tracker.py                        # 4-state tracker & 3-tier corroboration engine
│       └── processing/                           # SAR signal processing subpackage
│           ├── __init__.py
│           ├── alignment.py                      # Affine transform & grid validation
│           ├── calibration.py                    # Product-aware radiometric calibration
│           ├── log_ratio.py                      # Log-ratio differencing, tuning split, threshold, sieving
│           ├── mosaicking.py                     # Direct abutting slice assembler
│           └── speckle.py                        # Linear-space speckle filtering (Lee, Boxcar)
├── tests/                                        # Comprehensive Test Suite (94 Tests)
│   ├── __init__.py
│   ├── conftest.py                               # Synthetic test fixtures & grid generators
│   ├── run_tests.py                              # Standalone test suite runner
│   ├── test_four_state_tracker.py                # 13 Four-State Temporal Tracker tests
│   ├── test_pipeline_e2e.py                      # 3 Full-stack pipeline scenario tests
│   ├── test_pipeline_integration.py              # 8 Phase 2.3 integration tests
│   ├── test_processing.py                        # 22 SAR Signal Processing tests
│   ├── test_slice_assembler.py                   # 17 Direct Abutting Slice Assembler tests
│   └── test_stage1_contracts.py                  # 31 Schema & contract invariant tests
├── BHnMISnTRA_PRD.pdf                            # Historical v3 PRD reference document
├── GEMINI.md                                     # Antigravity Pro master operating prompt
├── INTEGRATION_HANDOFF.md                        # THIS DOCUMENT
├── PRD.md                                        # Authoritative Master PRD specification (v3.1)
├── README.md                                     # Module overview & quickstart documentation
└── .gitignore                                    # Git exclusion rules
```

---

## 4. Main Entry Point and Startup Commands

Member 1 is an **algorithmic scientific package and compute engine**, not a standalone web server or daemon process. It is imported and orchestrated by Member 2 (FastAPI Backend).

### Primary Programmatic Entry Point:
```python
from src.bhnmisntra_science.pipeline import run_scientific_pipeline
from src.bhnmisntra_science.config import InvestigationConfig
from src.bhnmisntra_science.processing.mosaicking import SlicePair

# Execute end-to-end investigation
result = run_scientific_pipeline(
    config=investigation_config,
    slice_data=slice_data_mapping,          # Mapping[str, SlicePair]
    raster_data=pre_assembled_raster_dict,  # Mapping[str, tuple[np.ndarray, AlignmentMetadata]]
    allow_missing_subsequent=True,          # Governed missing observation handling
    data_authenticity_tier="TIER 2 - PREPARED PILOT BENCHMARK",
)
```

### Direct CLI Verification Commands:
```powershell
# 1. Run all 94 acceptance unit & integration tests
python tests/run_tests.py

# 2. Run the Phase 2.4 Controlled Smoke Test Harness
python scratch/run_real_data_smoke_test.py

# 3. Query live NASA ASF DAAC for Sentinel-1 Track 165 granules
python scratch/check_asf_access.py

# 4. Query live NASA CMR & ASF for NISAR Kuttanad records
python scratch/inspect_kuttanad_nisar.py
```

---

## 5. Dependencies and Installation Commands

### 1. Minimal Runtime Installation (Standard Environment):
```bash
pip install "pydantic>=2.0.0" "numpy>=1.22.0,<2.0.0" "scipy>=1.8.0"
```

### 2. Local Editable Installation for Development:
```bash
# From workspace root:
pip install -e .
```

### 3. Optional Geographic Raster I/O Extensions:
```bash
pip install "rasterio>=1.3.0"
```

---

## 6. Required Environment Variables

Member 1 core algorithms are **entirely stateless and require no environment variables** for mathematical processing.

However, when activating satellite download utilities or live cloud ingestion pipelines:

| Variable Name | Purpose | Sensitivity Level |
| :--- | :--- | :--- |
| `EARTHDATA_USERNAME` | NASA Earthdata Login username for ASF archive access | Private Credential |
| `EARTHDATA_PASSWORD` | NASA Earthdata Login password for ASF archive access | Private Credential |
| `EARTHDATA_TOKEN` | Bearer Token for `datapool.asf.alaska.edu` / `nisar.asf.earthdatacloud.nasa.gov` | Secret Bearer Token |
| `AWS_ACCESS_KEY_ID` | Temporary STS credentials for direct S3 bucket reading (`s3://sds-n-cumulus-prod-nisar-products`) | Cloud Secret |
| `AWS_SECRET_ACCESS_KEY` | Temporary STS secret key for in-region Cumulus S3 bucket | Cloud Secret |
| `AWS_SESSION_TOKEN` | AWS STS session token obtained via `https://nisar.asf.earthdatacloud.nasa.gov/s3credentials` | Cloud Secret |

> **Security Rule**: Zero credentials or tokens may be hardcoded or committed to git. All credentials must reside in environment variables or user-level `~/.netrc` (`%USERPROFILE%\_netrc`).

---

## 7. APIs, Exported Functions, and Modules Provided

All public interfaces are exported through [`src/bhnmisntra_science/__init__.py`](file:///c:/Users/Diya/OneDrive/Apps/nasa/src/bhnmisntra_science/__init__.py):

### 1. Pipeline Orchestrator (`src.bhnmisntra_science.pipeline`)
- `run_scientific_pipeline(...) -> PipelineExecutionResult`: End-to-end execution from input ingestion through slice assembly, filtering, log-ratio differencing, sieving, 4-state tracking, and Evidence Ledger generation.
- `PipelineExecutionResult`: Immutable dataclass containing evidence status, masks, diff grids, and JSON ledger.

### 2. Spatial Assembly & Mosaicking (`src.bhnmisntra_science.processing.mosaicking`)
- `assemble_abutting_slices(...) -> AssembledRaster`: Direct abutting slice assembler that concatenates North and South Sentinel-1 frames onto a master grid without seam blurring.
- `SliceInput(data: np.ndarray, metadata: AlignmentMetadata, slice_id: str)`: Input container for individual frames.
- `SlicePair(slice_north: SliceInput, slice_south: SliceInput, ...)`: Pair of abutting along-track frames.
- `AssembledRaster(data: np.ndarray, metadata: AlignmentMetadata, provenance: dict)`: Assembled output.

### 3. Multi-Temporal Beat Test Tracker (`src.bhnmisntra_science.beat_test.tracker`)
- `evaluate_four_state_trajectory(...) -> TrajectoryEvaluationResult`: Evaluates a single spatial cluster across $N \ge 3$ subsequent acquisitions into `PERSISTENT_STAGNATION`, `RECEDING`, `RE_INUNDATED`, or `DRAINED`.
- `evaluate_mixed_spatial_trajectories(...) -> dict`: Evaluates independent spatial clusters across a scene, preventing large receding areas from masking unexplained localized surges.
- `track_change_regions(...) -> RegionTrackingResult`: Connected-component tracking between consecutive observation masks.

### 4. SAR Signal Processing (`src.bhnmisntra_science.processing`)
- `calibrate_sar_array(data: np.ndarray, metadata: CalibrationMetadata) -> np.ndarray`: Double-calibration guarded radiometric calibration returning decibels.
- `apply_speckle_filter(data_db: np.ndarray, filter_name: str, window_size: int) -> np.ndarray`: Linear-space speckle filtering (Lee, Boxcar) with log-bias prevention.
- `compute_log_ratio(ref_db: np.ndarray, comp_db: np.ndarray) -> np.ndarray`: Log-ratio backscatter differencing ($comp_{\text{dB}} - ref_{\text{dB}}$).
- `create_spatial_tuning_mask(shape, split_ratio, seed) -> np.ndarray`: Isolated spatial tuning split mask.
- `compute_threshold(diff_linear, config, mask) -> float`: Computes change threshold (Fixed dB, Robust MAD, Otsu).
- `generate_change_mask(diff_linear, threshold_linear, mmu_pixels, ...) -> tuple[np.ndarray, np.ndarray]`: Generates raw and MMU-sieved binary change masks.
- `validate_raster_alignment(meta_a, meta_b, ...) -> bool`: Validates CRS, resolution, and affine geotransforms.

### 5. Policies & Decision Logic (`src.bhnmisntra_science.policies`)
- `classify_final_evidence(...) -> tuple[EvidenceStatus, tuple[str, ...]]`: Deterministic evidence classifier.
- `evaluate_incidence_angle_pair(...) -> tuple[AngleComparisonOutcome, str]`: Angular divergence check.
- `evaluate_confounders_for_evidence_label(...) -> tuple[bool, str]`: Confounder impact evaluation.

---

## 8. Expected Input and Output Formats

### 1. Primary Input Configuration (`InvestigationConfig` Pydantic Model)
```json
{
  "investigation_id": "INV-KUTTANAD-2018-001",
  "study_area_id": "CORE_KUTTANAD_DELTA",
  "bbox": {
    "min_lon": 76.3300,
    "min_lat": 9.2500,
    "max_lon": 76.5500,
    "max_lat": 9.5500,
    "crosses_antimeridian": false
  },
  "phenomenon_type": "flood",
  "expected_behavior": "receding",
  "reference_acquisition": {
    "product_id": "S1A_IW_GRDH_1SDV_20180728_COMBINED",
    "acquisition_utc": "2018-07-28T00:41:08Z",
    "sensor": {
      "mission": "SENTINEL-1",
      "sensor_name": "C-SAR",
      "sensor_mode": "IW",
      "polarization": "VV",
      "frequency_band": "C",
      "look_direction": "right",
      "incidence_angle": { "quality": "available", "angle_deg": 38.45 }
    },
    "orbit": { "orbit_direction": "descending", "pass_type": "descending", "relative_orbit": 165 },
    "calibration": {
      "calibration_state": "calibrated_db",
      "provenance": {
        "calibration_source_doc": "Copernicus S1 IPF RTC",
        "decibel_reference_scale": "10*log10(sigma0)"
      }
    }
  },
  "comparison_acquisition": { "...": "Same schema as reference" },
  "subsequent_acquisitions": [
    { "...": "Acquisition 1 (observed)" },
    { "...": "Acquisition 2 (observed or missing)" },
    { "...": "Acquisition 3 (observed or missing)" }
  ],
  "parameters": {
    "speckle_filter_name": "boxcar",
    "speckle_window_size": 3,
    "threshold_strategy": { "strategy_type": "fixed_db", "drop_threshold_db": -3.5 },
    "min_mapping_unit_pixels": 10,
    "flood_growth_tolerance": 0.15,
    "sustained_overlap_ratio": 0.5,
    "min_spatial_coverage_ratio": 0.8,
    "min_valid_pixel_ratio": 0.8,
    "spatial_tuning_split_ratio": 0.5,
    "max_incidence_angle_divergence_deg": 2.0,
    "unavailable_incidence_angle_policy": "fail_validation"
  },
  "confounders": [
    {
      "confounder_id": "CONF-WATER-001",
      "name": "permanent_water_vembanad",
      "criticality": "critical",
      "state": "clear",
      "description": "JRC 85% occurrence baseline",
      "assessment_source": {
        "provider": "EC JRC",
        "dataset_name": "Global Surface Water",
        "url_or_doi": "https://doi.org/10.1038/nature20584",
        "window_start_utc": "2018-07-28T00:00:00Z",
        "window_end_utc": "2018-07-28T23:59:59Z"
      }
    }
  ],
  "output_dir": "outputs/kuttanad"
}
```

### 2. Primary Output (`PipelineExecutionResult` Payload)
```json
{
  "evidence_status": "unverified",
  "classification_reasons": [
    "PRD Hard Rule: Insufficient repeat observations (1 < 3). We make no claim."
  ],
  "beat_test_passed": true,
  "spatial_alignment_verified": true,
  "data_authenticity_tier": "TIER 3 - SYNTHETIC FIXTURE",
  "acquisition_dates": ["2018-07-28", "2018-08-21", "2018-09-02", "2018-09-14", "2018-09-26"],
  "temporal_states": ["PEAK", "RECEDING", "MISSING", "MISSING"],
  "coverage_metrics": {
    "subsequent_acquisitions_total": 3,
    "subsequent_acquisitions_valid": 1,
    "subsequent_acquisitions_missing": 2,
    "valid_subsequent_ratio": 0.3333
  },
  "baseline_change_stats": {
    "initial_change_pixels": 3000,
    "sieved_change_pixels": 2996,
    "sieved_change_area_km2": 0.2996,
    "retained_pixel_ratio": 0.9987
  },
  "slice_assembly_provenance": {
    "S1A_20180728": {
      "assembly_method": "DIRECT_ABUTTING_ASSEMBLY",
      "crs": "EPSG:32643",
      "master_shape": [200, 150],
      "seam_boundary_row": 80
    }
  },
  "scientific_limitations": [
    "PRD Hard Rule: Insufficient valid subsequent acquisitions (1 < 3). Final status is strictly UNVERIFIED.",
    "Empirical thresholds (15% area change tolerance, 50mm rainfall, 4.0 m/s wind) are PROVISIONAL engineering heuristics."
  ],
  "evidence_ledger": {
    "investigation_id": "INV-KUTTANAD-2018-001",
    "final_evidence_status": "unverified",
    "verification_timestamp_utc": "2026-11-14T18:20:00Z",
    "data_authenticity_badge": "TIER 3 - SYNTHETIC FIXTURE",
    "audit_hash": "sha256-..."
  }
}
```

---

## 9. Database and External Service Requirements

- **Database Requirements for Member 1**: **ZERO**. Member 1 is a stateless compute engine. It has no PostgreSQL, MySQL, Redis, or SQLite dependency. Member 2 may persist results in PostgreSQL / PostGIS.
- **External Web Services Queried**:
  1. **NASA Alaska Satellite Facility (ASF) DAAC REST API**:
     - Endpoint: `https://api.daac.asf.alaska.edu/services/search/param`
     - Protocol: HTTPS REST (Open, no auth required for search).
  2. **NASA Earthdata Common Metadata Repository (CMR)**:
     - Endpoint: `https://cmr.earthdata.nasa.gov/search/granules.json` and `collections.json`
     - Protocol: HTTPS REST (Open, no auth required for metadata).
  3. **NASA ASF Datapool (Sentinel-1 Archives)**:
     - Endpoint: `https://datapool.asf.alaska.edu/GRD_HD/SA/...`
     - Protocol: HTTPS Download (Requires NASA Earthdata Login).
  4. **NASA Earthdata Cloud (NISAR L2 GSLC/GCOV Archives)**:
     - Endpoint: `https://nisar.asf.earthdatacloud.nasa.gov/NISAR/...`
     - Protocol: HTTPS Download / AWS S3 (Requires Earthdata Login / AWS STS).

---

## 10. Current Test Results and Exact Test Commands

### Test Execution Command:
```powershell
python tests/run_tests.py
```

### Complete Test Results:
- **Total Test Count**: **94 Tests**
- **Passing**: **94 / 94 (100.0%)**
- **Failures / Errors**: **0**
- **Execution Duration**: **$0.033\text{ s} - 0.046\text{ s}$**

### Test Suite Module Breakdown:
| Test File | Count | Functionality Verified | Status |
| :--- | :---: | :--- | :---: |
| `tests/test_stage1_contracts.py` | 31 | Schema validation, Pydantic v2 immutability, Antimeridian boxes, UTC normalizers, discriminated unions, confounder matrix. | **PASS** |
| `tests/test_processing.py` | 22 | Radiometric calibration, double-calibration guard, speckle log-bias prevention, Robust MAD, Otsu, MMU sieving, spatial tuning split. | **PASS** |
| `tests/test_slice_assembler.py` | 17 | Direct abutting assembly, CRS validation, seam boundary handling, duplicate prevention, gap detection, nodata masking. | **PASS** |
| `tests/test_four_state_tracker.py` | 13 | 4-state trajectory tracking (`STAGNATION`, `RECEDING`, `RE_INUNDATED`, `DRAINED`), 3-tier corroboration, $N \ge 3$ PRD gate, mixed clusters. | **PASS** |
| `tests/test_pipeline_integration.py` | 8 | Phase 2.3 integration, `SlicePair` ingestion, missing acquisition governance, structured summary output. | **PASS** |
| `tests/test_pipeline_e2e.py` | 3 | Full pipeline end-to-end multi-temporal flood scenarios to `SUPPORTED` and `INCONCLUSIVE`. | **PASS** |

---

## 11. Known Bugs, Blockers, and Unfinished Features

### 1. Data Ingestion Gate (Active Blocker for Real-Pixel Validation)
- **Status**: **GATED BY USER CREDENTIALS**.
- **Description**: The local repository contains zero raw `.SAFE` archives or real `.tif` files due to download authentication gates (HTTP 403 / 401). All pipeline tests currently run on synthetic numpy fixtures (badged `TIER 3`).
- **Remediation**: Configure `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` in `~/.netrc` or supply pre-calibrated GeoTIFFs to `real_data/`.

### 2. Provisional Thresholds Awaiting Field Gauge Calibration
- **Status**: **PROVISIONAL ENGINEERING HEURISTICS**.
- **Description**: The $15\%$ area change tolerance, $50.0\text{ mm}$ rainfall trigger, and $4.0\text{ m/s}$ surface wind speed limit are marked provisional. They require empirical calibration against Central Water Commission (CWC) river gauges in Kuttanad.

### 3. JRC Permanent Water Raster Masking Layer
- **Status**: **PARTIALLY IMPLEMENTED**.
- **Description**: Permanent water confounders are currently assessed via `ConfounderRecord` metadata. Pixel-level masking requires downloading and rasterizing European Commission Joint Research Centre (JRC) Global Surface Water occurrence GeoTIFF tiles.

### 4. Local Range-Doppler Terrain Correction Engine
- **Status**: **INTENTIONALLY EXCLUDED BY DESIGN**.
- **Description**: The repository does not bundle local Range-Doppler SAR DEM orthorectification software (e.g. ESA SNAP / ISCE3). The pipeline assumes input rasters are already geocoded to map projection (`EPSG:32643`), which matches standard pre-calibrated RTC products (ASF HyP3 RTC or Google Earth Engine exports).

---

## 12. Existing Contracts and Assumptions for Other Repositories

Any repository (Backend, Frontend, or Ingestion Worker) integrating with Member 1 **MUST STRICTLY COMPLY** with the following immutable contracts:

1. **Non-Negotiable PRD Hard Gate ($N_{\text{valid}} \ge 3$)**:
   - If an investigation has fewer than 3 valid subsequent acquisitions ($N < 3$), the final status **MUST BE `UNVERIFIED`**.
   - No backend service or frontend UI may override this invariant or display positive flood claims on 1-pass or 2-pass observations.
2. **Missing Observations Never Mean Drainage**:
   - Missing observations (NaN, None, unacquired passes) must produce state `MISSING`. They must never be classified as `DRAINED` or interpolated as zero inundation.
3. **Zero Client-Side Secrets Enclave**:
   - Member 2 (FastAPI) must handle all external communication with NASA ASF and Earthdata. The frontend client bundle (Member 3) must never receive or expose Earthdata tokens or AWS S3 keys.
4. **No Synthetic Confidence Percentages**:
   - The platform strictly rejects synthetic probabilities (e.g. "97.8% flood confidence"). Outputs must report deterministic categorical evidence labels (`SUPPORTED`, `INCONCLUSIVE`, `UNVERIFIED`) alongside physical metrics (flooded area in $\text{km}^2$, backscatter drop in $\text{dB}$).
5. **Data Authenticity Badging**:
   - The UI must visibly display the `data_authenticity_tier` badge (`Tier 1 - Genuine`, `Tier 2 - Prepared Benchmark`, `Tier 3 - Synthetic Fixture`) on every view.
6. **Projected CRS Convention**:
   - All raster arrays passed into the pipeline must share a single projected coordinate system (e.g., `EPSG:32643` UTM Zone 43N) with north-up geotransforms. Geographic coordinates (`EPSG:4326`) are rejected at the raster processing level.

---

## 13. Exact Integration Requirements for Other BHRAMANASTHRA Modules

### 1. Connecting to Member 2 (FastAPI Backend)
- **Packaging**: Member 2 adds this repository as a submodule or pip dependency (`pip install -e ../nasa`).
- **Endpoints to Implement in Member 2**:
  - `POST /api/v1/investigations/feasibility`: Accepts BBox and date range; checks SAR track overlap (Track 165) and verifies that $\ge 3$ subsequent acquisitions exist before permitting investigation launch.
  - `POST /api/v1/investigations/run`: Deserializes request into `InvestigationConfig`, loads cached or downloaded rasters, and invokes `run_scientific_pipeline()`.
  - `GET /api/v1/investigations/{id}/ledger`: Returns `PipelineExecutionResult.evidence_ledger` as JSON.
  - `GET /api/v1/investigations/{id}/tiles/{z}/{x}/{y}.png`: Dynamic map tile server rendering `sieved_change_mask` and `diff_raster_db`.

### 2. Connecting to Member 3 (MapLibre / React Frontend)
- **Map Exploration**: Renders interactive map with 3 selection modes:
  1. *Administrative Boundary Selection* (Kerala Taluks / Panchayats)
  2. *Freehand Polygon Drawing*
  3. *Rectangle Bounding Box*
- **Progressive Complexity**:
  - *Tier 1 User*: Sees simple traffic-light cards (`Evidence Supported`, `Inconclusive`, `Unverified`), total flooded area in $\text{km}^2$, and timeline status.
  - *Advanced User*: Can expand scientific tabs to view dB histograms, MMU sieving details, orbit ephemerides, and the cryptographic Evidence Ledger.

### 3. Connecting to Member 4 (Evaluation & Verification Lead)
- Member 4 consumes `result.sieved_change_mask`, `result.diff_raster_db`, and `result.baseline_change_stats` to compute precision, recall, and intersection-over-union (IoU) against independent reference masks (e.g., Sentinel-2 optical NDWI masks from 26-Sep-2018).

---

## 14. Protected Files — Must Not Modify Without Coordination

The following files constitute the **scientific and mathematical foundation** of the BHRAMANASTHRA platform. Other team members must **NOT** modify or refactor these files without formal coordination:

| Protected File | Critical Invariants Encapsulated |
| :--- | :--- |
| `src/bhnmisntra_science/constants.py` | Frozen PRD numerical constants, MMU minimums, ratio cross-multipliers. |
| `src/bhnmisntra_science/enums.py` | Scientific type system (`EvidenceStatus`, `TemporalState`, `CalibrationState`). |
| `src/bhnmisntra_science/config.py` | Pydantic v2 schemas and strict validators. |
| `src/bhnmisntra_science/policies.py` | Core physical decision trees and classification rules. |
| `src/bhnmisntra_science/processing/mosaicking.py` | Direct abutting along-track slice assembly logic and seam handling. |
| `src/bhnmisntra_science/beat_test/tracker.py` | Four-state multi-temporal trajectory tracking and three-tier corroboration. |
| `src/bhnmisntra_science/pipeline.py` | Master orchestrator and Evidence Ledger builder. |
| `research/ACQUISITION_MANIFEST.md` | Authoritative Sentinel-1 Track 165 granule manifest for Kerala. |
| `research/PHASE_1_5_SCIENTIFIC_SPECIFICATION.md` | Frozen scientific specification governing all pipeline behaviors. |
| `tests/*.py` | Acceptance test harness enforcing 94 non-negotiable invariants. |

---

## 15. Implementation Status Breakdown

### Implemented and Tested (100% Verified by Acceptance Tests)
- [x] Pydantic v2 metadata contracts, bounding box validators, and UTC normalizers (`test_stage1_contracts.py` — 31 tests).
- [x] Product-aware radiometric calibration with double-calibration guard (`test_processing.py`).
- [x] Linear-space speckle filtering (Lee, Boxcar) with log-bias prevention (`test_processing.py`).
- [x] Log-ratio differencing and spatial tuning split partitioning (`test_processing.py`).
- [x] Threshold computation (Fixed dB, Robust MAD, Otsu) and MMU sieving (`test_processing.py`).
- [x] Direct abutting Sentinel-1 slice assembler without overlap blending (`test_slice_assembler.py` — 17 tests).
- [x] Four-State Temporal Beat Test Tracker with Three-Tier Physical Corroboration (`test_four_state_tracker.py` — 13 tests).
- [x] Governed missing/invalid observation handling without false drainage (`test_pipeline_integration.py` — 8 tests).
- [x] Hard PRD Gate: $N_{\text{valid}} < 3 \implies \text{UNVERIFIED}$ strictly enforced (`test_pipeline_integration.py`).
- [x] End-to-end scientific pipeline orchestrator and Evidence Ledger generator (`test_pipeline_e2e.py` — 3 tests).

### Implemented but Not Tested on Real Satellite Rasters
- [ ] Direct Level-1 GRDH GeoTIFF file disk loader (`SlicePair.from_geotiff_files` stub): Code logic exists, but disk I/O remains unexercised on real `.SAFE` rasters due to download authentication gates.
- [ ] AWS S3 Cumulus direct streaming via STS temporary credentials: Code hooks and endpoints are mapped, but unexercised without active AWS IAM credentials.

### Partially Implemented
- [ ] Pre-Investigation Feasibility Check: Orbital overlap calculation logic exists in `policies.py`, but standalone HTTP service endpoint belongs in Member 2 FastAPI repo.
- [ ] Automated NASA Earthdata Downloader: Live search query scripts exist in `scratch/`, but automated binary archive download requires local `.netrc` credential provisioning.
- [ ] JRC Global Surface Water permanent water mask: Assessment metadata structures exist; automated raster tile fetching and raster masking requires tile pipeline.

### Not Implemented (Belongs to Other Team Members)
- [ ] FastAPI HTTP REST API endpoints and server routes (Member 2).
- [ ] PostgreSQL / PostGIS database models and migrations (Member 2).
- [ ] React / MapLibre GL map-first user interface and selection tools (Member 3).
- [ ] Local DEM Range-Doppler SAR orthorectification engine (Intentionally replaced by pre-calibrated RTC products).

---

**Report Prepared by**:  
*Lead Data & Scientific Intelligence Specialist (Member 1)*  
*BHRAMANASTHRA Project — NASA Space Apps Challenge 2026*

