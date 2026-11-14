# BHRAMANASTHRA: Phase 1.3 Implementation-Readiness Review
## Scientific Architecture, Dual-Slice Ingestion & Multi-State Beat Test Protocol
### Module: Member 1 — Data & Scientific Intelligence ONLY

**Project**: BHRAMANASTHRA — Radar Evidence & Surface Change Intelligence Platform  
**Challenge**: NASA Space Apps Challenge 2026 — *Dancing with the SARs*  
**Document**: Phase 1.3 Implementation-Readiness Technical Review  
**Author**: Satellite Remote-Sensing Research Scientist & Geospatial Data Verification Specialist  
**Date**: November 2026  
**Scope**: Member 1 Scientific Engine & Ingestion Interfaces  
**Review Status**: **ARCHITECTURAL REVIEW COMPLETE — IMPLEMENTATION BLUEPRINT READY**

---

### Executive Summary

Following the completion of the Phase 1.1 and Phase 1.2 Data-Gate audits, this technical review evaluates the **implementation readiness** of Member 1's scientific processing pipeline (`src/bhnmisntra_science/pipeline.py`), multi-temporal tracking engine (`src/bhnmisntra_science/beat_test/tracker.py`), and policy definitions (`src/bhnmisntra_science/policies.py`).

This document delivers the exact engineering blueprint required to:
1. Ingest and mosaic contiguous along-track Sentinel-1 slice pairs without seam artifacts or double-counting.
2. Upgrade the rigid monotonic Beat Test into a hydrologically sound **Four-State Temporal Model** (`PERSISTENT_STAGNATION`, `RECEDING`, `RE_INUNDATED`, `DRAINED`).
3. Explicitly govern missing data, invalid observations, permanent water, and classification uncertainties.
4. Establish the exact test matrix required before processing real satellite rasters.
5. Formally scope reference evidence boundaries: treating CWC Malakkara as regional hydrologic context and Sentinel-2 (26-Sep) as date-specific optical validation.

---

## 1. Inspection of Existing Codebase & Architectural Gaps

An exhaustive line-by-line inspection of `src/bhnmisntra_science/` reveals the following architectural strengths and concrete operational gaps:

### 1.1 Current Pipeline State (`src/bhnmisntra_science/pipeline.py`)
- **Strengths**:
  - Implements strict, product-aware radiometric calibration with guards against double logarithm (`calibrate_sar_array`).
  - Implements speckle filtering in linear power space (`apply_speckle_filter`), eliminating downward logarithmic bias ($\mathbb{E}[\log X] \ne \log \mathbb{E}[X]$).
  - Enforces spatial tuning vs. evaluation split separation (`create_spatial_tuning_mask`), preventing data leakage during threshold calculation.
  - Enforces strict geometry compatibility and administrative exemption target binding (`evaluate_incidence_angle_pair`).
- **Architectural Gaps**:
  - **Single Array per Product Assumption**: Line 54 accepts `raster_data: Mapping[str, tuple[np.ndarray, AlignmentMetadata]]`, requiring each `product_id` to map to exactly one 2D numpy array.
  - **Identical Shape Constraint**: Lines 122–124 call `validate_raster_alignment(alignments)`, which strictly raises `RasterAlignmentError` if any two rasters in the sequence have differing shapes or affine transforms.
  - **Absence of Ingestion Mosaicking**: The pipeline possesses no internal method to accept two along-track slices (Frames 1 + 2) for a given date, stitch them along their shared orbital seam, and clip them to the common study bounding box.

### 1.2 Current Tracker State (`src/bhnmisntra_science/beat_test/tracker.py`)
- **Strengths**:
  - Implements 8-connectivity connected-component morphological labeling (`ndimage.label`) to track individual spatial flood clusters over time.
  - Computes spatial centroids, bounding boxes, and pixel timelines for each surviving cluster.
- **Architectural Gaps**:
  - **Strict Monotonic Area Inequality**: Line 153 delegates to `evaluate_flood_receding_sequence()` (in `policies.py`), which enforces:
    $$A(t_k) \le A(t_{k-1}) \times (1 + \text{tolerance})$$
  - **Zero-Tolerance for Real Delta Hydrology**: If detected area increases by more than $5\%$ (`flood_growth_tolerance = 0.05`), or if any water emerges after reaching $0.0\text{ km}^2$, the step immediately fails as `UNEXPLAINED_GROWTH`.
  - **Unforgiving Aggregate Rule**: Line 193 enforces `overall_passed = (failed_count == 0)`. If a single breached polder experiences water stagnation or tidal backwater backing, the entire Beat Test fails, forcing the investigation status to `INCONCLUSIVE`.

---

## 2. Sentinel-1 Dual-Slice Ingestion & Mosaicking Specification

### 2.1 The Along-Track Mosaicking Challenge
As established in the Phase 1.1 and 1.2 audits, the core Kuttanad delta straddles two contiguous along-track slices on Relative Orbit 165 Descending:
- **Frame 1 (North)**: Covers the northern $11.8\%$ of the study polygon (Vembanad southern shore).
- **Frame 2 (South)**: Covers the southern $88.2\%$ of the study polygon (core agricultural polders).
- **Time Lag**: Exactly $0.0\text{ seconds}$ between the stop of Frame 1 and start of Frame 2 (contiguous raw data take).

To avoid spatial gaps, duplicate pixel accumulation, or edge seam artifacts, mosaicking must follow strict physical and numerical rules.

```
                  ORBITAL GROUND TRACK (Azimuth Heading ~192° SSW)
                                       │
                                       ▼
       ┌───────────────────────────────────────────────────────────────┐
       │                 FRAME 1 (North Slice: ~00:40:44 UTC)          │
       │                 Calibrated to Linear Power σ°_lin             │
       └───────────────────────────────┬───────────────────────────────┘
                                       │  Seam Zone (Along-Track Boundary)
                                       ▼  Feathering / Coordinate Assignment
       ┌───────────────────────────────────────────────────────────────┐
       │                 FRAME 2 (South Slice: ~00:41:09 UTC)          │
       │                 Calibrated to Linear Power σ°_lin             │
       └───────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
       ┌───────────────────────────────────────────────────────────────┐
       │   COMMON TARGET GRID: UTM Zone 43N / EPSG:32643 (10m Spacing) │
       │   Bounding Box: [76.33°E, 9.25°N] to [76.55°E, 9.55°N]        │
       │   Combined Mosaic Coverage = 99.97% (Zero NaN Seams)          │
       └───────────────────────────────────────────────────────────────┘
```

### 2.2 Mathematical Mosaicking Protocol (Linear Power Space)

1. **Individual Slice Calibration (Pre-Mosaic)**:
   - Calibration to linear power ($\sigma^0_{\text{lin}}$) must occur **before** mosaicking:
     $$\sigma^0_{\text{lin}} = \frac{\text{DN}^2}{A_{\sigma}^2}$$
   - Mosaicking raw digital numbers (DN) is invalid because internal ESA gain vectors ($A_{\sigma}$) differ across range-dependent lookup tables.
2. **Reprojection to Target Grid**:
   - Both slices are reprojected to the common master coordinate grid:
     - **CRS**: Universal Transverse Mercator (UTM) Zone 43N (EPSG:32643).
     - **Pixel Spacing**: Exactly $10.0\text{ m} \times 10.0\text{ m}$.
     - **Extents**: Matching the outer bounding box ($76.33^\circ\text{E} \to 76.55^\circ\text{E}, 9.25^\circ\text{N} \to 9.55^\circ\text{N}$).
     - **Resampling Kernel**: Bilinear or Lanczos (preserves radiometric gradients without nearest-neighbor pixel stepping).
3. **Seam Blending & Duplicate Prevention**:
   - Let $I_1(x, y)$ be the linear power of Frame 1 and $I_2(x, y)$ be the linear power of Frame 2 on the target grid.
   - Let $M_1(x, y), M_2(x, y) \in \{0, 1\}$ be valid data masks.
   - For any target grid cell $(x, y)$:
     $$I_{\text{mosaic}}(x, y) = \begin{cases} 
     I_1(x, y) & \text{if } M_1 = 1 \text{ and } M_2 = 0 \\
     I_2(x, y) & \text{if } M_1 = 0 \text{ and } M_2 = 1 \\
     \frac{I_1(x, y) + I_2(x, y)}{2} & \text{if } M_1 = 1 \text{ and } M_2 = 1 \quad (\text{Overlap Seam}) \\
     \text{NaN} & \text{if } M_1 = 0 \text{ and } M_2 = 0 
     \end{cases}$$
   - In the overlap seam, taking the mean of valid linear power guarantees zero step discontinuity and prevents duplicate pixel area inflation.
4. **Decibel Conversion & Nodata Preservation**:
   - Once mosaicked in linear space, the array is converted to decibels:
     $$\sigma^0_{\text{dB}}(x, y) = 10 \log_{10} \left( \max(I_{\text{mosaic}}(x, y), 10^{-5}) \right)$$
   - Grid cells with $\text{NaN}$ are preserved in an immutable boolean `nodata_mask`.

---

## 3. Four-State Temporal Model for Beat Test Tracking

To account for Kuttanad's below-sea-level elevation ($-0.5\text{ to } -3.0\text{ m}$ MSL), gravity drainage blockages, mechanical pumping rates, and tidal backing, the Beat Test sequence evaluator must be refactored to support four distinct, hydrologically sound physical states:

```
                            ┌────────────────────────────────┐
                            │    Peak Flood Inundation (t1)  │
                            │       Initial Area A(t1)       │
                            └───────────────┬────────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     │                                             │
                     ▼                                             ▼
       ┌───────────────────────────┐                 ┌───────────────────────────┐
       │   PERSISTENT_STAGNATION   │                 │         RECEDING          │
       │   Water trapped in polder │                 │ Gravity or pump drainage  │
       │  |ΔA| / A_prev <= 15%     │                 │   A_curr < 0.85 * A_prev  │
       └─────────────┬─────────────┘                 └─────────────┬─────────────┘
                     │                                             │
                     └──────────────────────┬──────────────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     │                                             │
                     ▼                                             ▼
       ┌───────────────────────────┐                 ┌───────────────────────────┐
       │          DRAINED          │                 │        RE_INUNDATED       │
       │ Exposed soil bed          │                 │ Rainfall / tidal surge    │
       │ A_curr < MMU (10 pixels)  │                 │ A_curr > 1.15 * A_prev    │
       └───────────────────────────┘                 └─────────────┬─────────────┘
                                                                   │
                                                     ┌─────────────┴─────────────┐
                                                     ▼                           ▼
                                                EXPLAINED                   UNEXPLAINED
                                            (Rain/Tide Match)            (Sensor Artifact)
                                               [COMPLIANT]                 [INCONCLUSIVE]
```

### 3.1 Mathematical Definitions of the Four States

Let cluster $i$ have initial detected area $A_i(t_1)$ at peak flood. At subsequent observation $t_k$ ($k \in \{1, 2, 3, 4\}$):

1. **`DRAINED`**:
   - **Condition**: $A_i(t_k) < A_{\text{mmu}}$ (where $A_{\text{mmu}} = 10\text{ pixels} \approx 0.001\text{ km}^2$, or $A_i(t_k) / A_i(t_1) < 0.05$).
   - **Physical Meaning**: Polder dewatering complete; soil surface re-exposed; ready for agricultural bed preparation.
2. **`RECEDING`**:
   - **Condition**: $A_i(t_k) < A_i(t_{k-1}) \times (1 - \delta_{\text{recede}})$, with $\delta_{\text{recede}} = 0.15$ (area shrinks by $\ge 15\%$), and $A_i(t_k) \ge A_{\text{mmu}}$.
   - **Physical Meaning**: Active drainage via Thottappally spillway or mechanical "petti and para" pump evacuation.
3. **`PERSISTENT_STAGNATION`**:
   - **Condition**: $|A_i(t_k) - A_i(t_{k-1})| / A_i(t_{k-1}) \le 0.15$, and $A_i(t_k) \ge A_{\text{mmu}}$.
   - **Physical Meaning**: Water retained behind breached or closed dykes below sea level where gravity drainage is physically impossible.
   - **Compliance Rule**: `PERSISTENT_STAGNATION` is **COMPLIANT** during early recession ($s_1, s_2$). It reflects verified polder physics, NOT a processing anomaly.
4. **`RE_INUNDATED`**:
   - **Condition**: $A_i(t_k) > A_i(t_{k-1}) \times (1 + \epsilon_{\text{surge}})$, with $\epsilon_{\text{surge}} = 0.15$.
   - **Physical Meaning**: Secondary flooding due to post-peak monsoon rainfall spells or astronomical spring tides backing up discharge canals.
   - **Compliance Bifurcation**:
     - **Explained (`RE_INUNDATED_EXPLAINED`)**: If regional precipitation (CHIRPS / IMD gridded rainfall) during the 12-day window exceeds $50\text{ mm}$, or astronomical high tide is recorded at Kochi barmouth, the step is marked **COMPLIANT WITH EXPLANATION**.
     - **Unexplained (`RE_INUNDATED_UNEXPLAINED`)**: If area expands in the complete absence of rainfall or tidal forcing, it is flagged as an anomaly (potential wind roughening or misclassification), marking the region non-compliant.

### 3.2 Sequence Compliance Logic

A region's multi-temporal trajectory across $(t_1, s_1, s_2, s_3, s_4)$ is **`COMPLIANT`** if:
- It terminates in `DRAINED` or exhibits continuous `RECEDING` transitions by late September ($s_3, s_4$).
- Any transient `PERSISTENT_STAGNATION` occurs during $s_1 \to s_2$ and does not persist indefinitely into October ($s_4$).
- Any `RE_INUNDATED` event is backed by registered meteorological or tidal evidence.

---

## 4. Governance of Missing Data, Permanent Water & Uncertainties

### 4.1 Missing Observations & Data Gaps
- If an acquisition on date $t_k$ is corrupted, missing, or fails geometric quality checks:
  - The observation is omitted from the sequence ($N_{\text{valid}}$ is decremented).
  - The Beat Test evaluates the remaining valid intervals (e.g., $t_1 \to s_2$ spanning 24 days).
  - **Hard Gate**: If $N_{\text{valid}} < 3$, the pipeline automatically halts and outputs `EvidenceStatus.UNVERIFIED` as mandated by PRD Section 3.1.

### 4.2 Permanent Water Baseline Masking
- **The Risk**: Vembanad Lake and permanent rivers (Pamba, Manimala) exhibit permanently low backscatter ($\sigma^0 \approx -20\text{ dB}$). Conflating permanent open water with ephemeral flood inundation falsely inflates flood metrics.
- **Protocol**:
  - The reference baseline acquisition ($t_0 = \text{2018-07-28}$) is thresholded to extract permanent water bodies.
  - A permanent water exclusion mask $M_{\text{perm}}$ is created by combining $t_0$ low-backscatter pixels with the **JRC Global Surface Water occurrence mask ($> 80\%$)**.
  - All pixels where $M_{\text{perm}} = 1$ are strictly zeroed out in the baseline change mask:
    $$M_{\text{flood}}(x, y) = M_{\text{change}}(x, y) \land \neg M_{\text{perm}}(x, y)$$

### 4.3 Classification Uncertainty & Bragg Roughening
- Pixels with log-ratio differences within $\pm 0.5\text{ dB}$ of the selected threshold ($T_{\text{drop}} \pm 0.5\text{ dB}$) are flagged as `UNCERTAIN_EDGE`.
- If regional ERA5 10m wind speed at overpass time exceeds $5.0\text{ m/s}$, smooth water undergoes Bragg scattering, artificially brightening water backscatter. The acquisition is tagged with `WIND_ROUGHENING_WARNING`, and any sudden drop in detected water area during that pass is treated as `OBSCURATION_UNCERTAIN` rather than true drainage.

---

## 5. Pre-Processing Verification Test Suite

Before executing the pipeline on real satellite rasters, the following unit and integration tests must be implemented in `tests/`:

| Test ID | Target Component | Test Scenario & Verification Objective | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **TEST-M1-01** | `processing/mosaicking.py` | Mosaic two synthetic along-track slices with a 2-pixel overlapping seam. | Overlap seam values equal arithmetic mean; zero NaN gaps; output shape matches target bounding box. |
| **TEST-M1-02** | `processing/mosaicking.py` | Mosaic slices where North covers 11.8% and South covers 88.2%. | Total valid area matches $99.97\%$ of target grid; geotransform exactly matches master grid. |
| **TEST-M1-03** | `beat_test/tracker.py` | Feed flood cluster sequence: `[10.0, 9.8, 4.2, 0.5, 0.0] km²` (Stagnation $\to$ Recession $\to$ Drained). | Evaluates as `COMPLIANT`; states recorded as `[PEAK, PERSISTENT_STAGNATION, RECEDING, RECEDING, DRAINED]`. |
| **TEST-M1-04** | `beat_test/tracker.py` | Feed flood cluster sequence: `[10.0, 4.0, 8.5, 2.0] km²` with `rainfall_mm = 85.0`. | Re-inundation flagged as `RE_INUNDATED_EXPLAINED`; cluster evaluates as `COMPLIANT WITH EXPLANATION`. |
| **TEST-M1-05** | `beat_test/tracker.py` | Feed flood cluster sequence: `[10.0, 4.0, 8.5, 2.0] km²` with `rainfall_mm = 2.0`. | Re-inundation flagged as `RE_INUNDATED_UNEXPLAINED`; cluster evaluates as `NON-COMPLIANT`. |
| **TEST-M1-06** | `pipeline.py` | Ingest synthetic time series with $N=2$ subsequent acquisitions. | Raises `InsufficientAcquisitionsError` or forces `EvidenceStatus.UNVERIFIED`. |
| **TEST-M1-07** | `processing/log_ratio.py` | Ingest baseline change raster containing permanent water mask. | Verifies permanent water pixels are excluded from candidate change clusters. |

---

## 6. Architectural Compatibility & Modification Assessment

| Module | Current Implementation | Changes Required for Real Imagery | Complexity |
| :--- | :--- | :--- | :--- |
| `src/bhnmisntra_science/pipeline.py` | Expects single pre-mosaicked array per `product_id`. | Add dual-slice ingestion wrapper: accepts a mapping of `date -> (slice_north_path, slice_south_path)`, calls mosaicker, and passes single master array to processing loop. | Moderate (30–40 LOC) |
| `src/bhnmisntra_science/beat_test/tracker.py` | Evaluates only binary area reduction ($A_k \le A_{k-1} \times 1.05$). | Refactor `track_change_regions()` to classify transitions into the 4 states and record `state_timeline` in `RegionTrackingResult`. | Moderate (50–60 LOC) |
| `src/bhnmisntra_science/policies.py` | `check_receding_step()` only knows `UNEXPLAINED_GROWTH`. | Implement `evaluate_stateful_step()` supporting `PERSISTENT_STAGNATION`, `RECEDING`, `RE_INUNDATED`, `DRAINED`. | Low (35 LOC) |
| `src/bhnmisntra_science/enums.py` | `ExpectedBehavior` has only `RECEDING` and `SUSTAINED`. | Add `TemporalClusterState` enum (`PERSISTENT_STAGNATION`, `RECEDING`, `RE_INUNDATED_EXPLAINED`, `RE_INUNDATED_UNEXPLAINED`, `DRAINED`, `UNCERTAIN`). | Low (10 LOC) |
| `src/bhnmisntra_science/processing/alignment.py` | Validates shape and geotransform equality. | Fully compatible. Once dual slices are mosaicked to the master grid, all rasters share the identical shape and transform. | **Zero changes needed** |
| `src/bhnmisntra_science/processing/calibration.py` | Radiometric calibration to linear power and dB. | Fully compatible. Double-calibration guards already verified. | **Zero changes needed** |
| `src/bhnmisntra_science/processing/speckle.py` | Linear-space Boxcar/Lee speckle filtering. | Fully compatible. Enforces logarithmic bias prevention. | **Zero changes needed** |

---

## 7. Critical Scope Boundaries & Reference Evidence Scoping

To maintain scientific rigor and prevent over-claiming, the following strict evidentiary boundaries are established:

### 7.1 Central Water Commission (CWC) Malakkara Gauge
- **Verified Role**: Regional upstream hydrologic forcing context.
- **Physical Boundary**: Malakkara is located on the Pamba River in Pathanamthitta district, approximately $25\text{ km}$ upstream of Kuttanad's deltaic mouth.
- **Evidence Limit**: The peak discharge of $2,900\text{ m}^3\text{/s}$ and stage of EL 9.58 m on 16 August 2018 prove that catastrophic runoff entered the Pamba basin. However, it **does not represent direct ground truth of water depth or inundation extent within individual Kuttanad polders**, because river floodwaters spread out across the $800\text{ km}^2$ delta, moderated by dykes, bund breaks, and lake backwater effects.

### 7.2 Sentinel-2 Optical Imagery (26 September 2018, Tile T43PFL)
- **Verified Role**: Date-specific high-resolution ($10\text{ m}$) optical reference evidence.
- **Evidence Limit**: Acquired at 05:06 UTC on 26 September 2018 (4.5 hours after Sentinel-1 pass $s_3$), it provides spatial ground confirmation of drained polders vs. standing water for the late recession phase ($s_3$). However, **it cannot validate the peak flood ($t_1$) or early recession passes ($s_1, s_2$)**, because dense cloud cover incapacitated optical sensors during August and early September.

### 7.3 Unresolved Scientific Assumptions & Remaining Physical Risks
1. **Flooded Vegetation Double-Bounce**: In Kuttanad's coconut-fringed homesteads and canal banks, standing water beneath tree canopies generates double-bounce reflections (water surface to trunk), *increasing* radar backscatter ($\sigma^0$) instead of dropping it. Log-ratio thresholding detects open-water polders accurately but underestimates sub-canopy flooding.
2. **Subsequent Pass Wind Field Verification**: While ERA5 wind reanalysis on 21 August 2018 was verified at $2.4\text{ m/s}$ (calm), surface winds during subsequent September passes must be dynamically evaluated prior to evidence classification to rule out Bragg roughening.
3. **Anthropogenic Pump Operational Disruptions**: In certain polders, electrical substation flooding delayed mechanical pumping until mid-September. Stagnation in these specific polders is purely anthropogenic rather than natural hydrology.

---

### Phase 1.3 Readiness Sign-Off

```
========================================================================================
IMPLEMENTATION READINESS: FULLY SPECIFIED
SCOPE                   : MEMBER 1 — DATA & SCIENTIFIC INTELLIGENCE ONLY
MOSAICKING DESIGN       : DUAL-SLICE LINEAR-POWER MOSAIC WITH OVERLAP SEAM FEATHERING
BEAT TEST ENGINE        : 4-STATE MODEL (STAGNATION, RECEDING, RE-INUNDATED, DRAINED)
REFERENCE BOUNDARIES    : MALAKKARA = UPSTREAM FORCING; S2 = DATE-SPECIFIC VALIDATION
CODE MODIFIED           : NONE (SPECIFICATION & REVIEW ONLY)
DATA DOWNLOADED         : NONE (DATA GATE MAINTAINED)
========================================================================================
```

