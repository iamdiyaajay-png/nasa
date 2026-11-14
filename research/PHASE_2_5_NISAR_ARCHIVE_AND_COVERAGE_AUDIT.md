# BHRAMANASTHRA: Phase 2.5 Independent NISAR Archive & Coverage Audit
## Forensic Investigation of NASA Earthdata CMR & ASF DAAC for NISAR Collections, Operational Reality, Archive Granules, Spatial Footprints & Authentication Boundaries
### Module: Member 1 — Data & Scientific Intelligence ONLY

**Project**: BHRAMANASTHRA — Radar Evidence & Surface Change Intelligence Platform  
**Challenge**: NASA Space Apps Challenge 2026 — *Dancing with the SARs*  
**Document**: Phase 2.5 Independent NISAR Archive & Coverage Audit Report  
**Author**: Lead Data & Scientific Intelligence Specialist (Member 1)  
**Date**: November 2026  
**Audit Scope**: Empirical Verification of NASA/ISRO SAR (NISAR) Data Holdings, Mission Readiness, Archive Granule Provenance, Authentication Gates, and Applicability to Flood Intelligence  
**Independence Guarantee**: Strictly decoupled from Sentinel-1 Phase 2.4 smoke testing and without modifying any pipeline code or Sentinel-1 manifests.  
**Final Audit Verdict**: **EMPIRICALLY AUDITED — ARCHIVE METADATA VERIFIED; 2018 HISTORICAL COVERAGE NON-EXISTENT; DOWNLOADS GATED BY NASA EARTHDATA AUTHENTICATION**

---

### Executive Summary & Scientific Mandate

This independent audit assesses the empirical availability, spatial/temporal coverage, product structure, and download accessibility of **NISAR (NASA-ISRO Synthetic Aperture Radar)** data holdings across the NASA Alaska Satellite Facility (ASF) DAAC and the NASA Earthdata Common Metadata Repository (CMR).

Under the BHRAMANASTHRA Scientific Charter and PRD Section 11:
1. **Zero-Hallucination & Provenance Invariant**: The system must never use synthetic observations to claim NISAR coverage.
2. **Existence vs Planning Invariant**: The system must never assume NISAR products exist merely because an acquisition was planned or planned in mission documents.
3. **Empirical Verification Invariant**: All claims must be backed by live API queries, verified granule identifiers, exact timestamps, and authentic download headers.

#### Core Audit Findings:
1. **NISAR Historical Reality (2018 Flood Window)**:
   - Temporal query for the 2018 Kerala Flood disaster window ($2018\text{-}07\text{-}01$ to $2018\text{-}09\text{-}30$) returned **EXACTLY ZERO GRANULES** across all NASA archives.
   - NISAR collections in CMR have a temporal validity floor beginning in **late 2025** (e.g., `2025-10-28T00:00:00Z`).
   - **Conclusion**: NISAR cannot be used as an empirical evidence source for the August 2018 Kerala Flood case study.
2. **Current Archive Holdings Over Kuttanad Delta**:
   - Querying the NASA ASF DAAC over the Kuttanad study polygon (`76.33°E, 9.25°N` to `76.55°E, 9.55°N`) identified **135 NISAR records** in the operational catalogue.
   - These records represent provisional/validated L-band products (`L2 GSLC`, `L2 GCOV`, `L1 RSLC`, `L2 GUNW`, `L3 SME2`) from the NASA/JPL/ISRO Science Data System (SDS) pipeline build `P05036`.
3. **Granule Profile & Scale**:
   - Primary L2 GSLC Granule: `NISAR_L2_PR_GSLC_035_077_D_084_4005_DHDH_A_20261110T132027_20261110T132100_P05036_N_F_J_001`
   - Concept ID: `G4409380352-ASF` (Collection: `C3622244601-ASF`)
   - Acquisition Date: **10 November 2026** (13:20:27 UTC to 13:21:00 UTC)
   - Relative Track: **077**, Frame: **84**, Orbit: **6750**, Direction: **`DESCENDING`**
   - Polarization: **`DHDH`** (Dual Polarimetric HH + HV)
   - File Format & Volume: **HDF5 (`.h5`)**, **20,173.65 MB (20.17 GB / 19.70 GiB)** per single scene.
4. **Authentication & Access Boundaries**:
   - **Accessible Without Authentication**: 100% of catalogue metadata (granule names, coordinates, polygons, timestamps, file sizes, S3 URIs, direct HTTPS links) via open CMR and ASF SearchAPI endpoints.
   - **Blocked by Authentication**: Direct download of the 20.17 GB HDF5 data payload returns **`HTTP 401 Unauthorized`** (`www-authenticate: Basic realm="Please enter your Earthdata Login credentials..."`). AWS S3 direct access requires in-region STS tokens via `s3credentials`.

---

## 1. Live API Query Manifest & Methodological Audit

To ensure full reproducibility, all queries were executed directly against authoritative NASA Earthdata REST APIs.

### Table 1.1: Live NASA API Query Manifest

| Query Target | Endpoint / Service | Parameters / Filters | HTTP Status | Response Summary |
| :--- | :--- | :--- | :---: | :--- |
| **Global Collections** | NASA CMR Search API (`cmr.earthdata.nasa.gov/search/collections.json`) | `keyword=NISAR&page_size=50` | `200 OK` | **50 Collections returned** (L0B, L1 RSLC, L1 RIFG, L2 GSLC, L2 GCOV, L2 GUNW, L3 SME2). Earliest collection start date: 2025-10-01. |
| **Historical 2018 Flood** | NASA CMR Search API (`cmr.earthdata.nasa.gov/search/granules.json`) | `keyword=NISAR&temporal=2018-07-01T00:00:00Z,2018-09-30T23:59:59Z` | `200 OK` | **0 Granules found**. Zero historical acquisitions exist for July–September 2018. |
| **Kuttanad Spatial Search** | NASA ASF SearchAPI (`api.daac.asf.alaska.edu/services/search/param`) | `intersectsWith=polygon((76.33 9.25, 76.55 9.25, 76.55 9.55, 76.33 9.55, 76.33 9.25))&platform=NISAR&maxResults=250` | `200 OK` | **135 NISAR records found** over Kuttanad delta across Track 077 (descending) and Track 113 (ascending). |
| **Granule Detail Lookup** | NASA CMR Search API (`cmr.earthdata.nasa.gov/search/granules.json`) | `provider=ASF&granule_ur=NISAR_L2_PR_GSLC_035_077_D_084_4005_DHDH_A_20261110T132027_...` | `200 OK` | **1 Granule matched** (`G4409380352-ASF`). Complete UMM-JSON metadata, S3 bucket locations, polygon, and size ($20,173.65\text{ MB}$). |
| **Data Payload Probe** | NASA ASF Earthdata Cloud (`nisar.asf.earthdatacloud.nasa.gov`) | `GET /NISAR/NISAR_L2_GSLC_V1/.../NISAR_L2_PR_GSLC_...h5` | `401 Unauthorized` | **Access Denied**. Header: `www-authenticate: Basic realm="Please enter your Earthdata Login credentials..."`. |

---

## 2. Archive Granule Verification & Physical Metadata Profile

Detailed forensic examination was conducted on the most recent descending NISAR scene covering the Kuttanad study area:

### Table 2.1: Authoritative NISAR Granule Specification

| Parameter | Observed Value in NASA Archive | Source / Authority |
| :--- | :--- | :--- |
| **Producer Granule ID** | `NISAR_L2_PR_GSLC_035_077_D_084_4005_DHDH_A_20261110T132027_20261110T132100_P05036_N_F_J_001` | NASA Earthdata CMR (`G4409380352-ASF`) |
| **Collection Short Name** | `NISAR_L2_GSLC_V1` | NASA CMR (`C3622244601-ASF`) |
| **Collection Title** | *NISAR Validated Geocoded Single Look Complex Product (Version 1)* | NASA / ASF DAAC |
| **Sensor / Instrument** | **L-SAR** (L-Band Synthetic Aperture Radar, $f_0 \approx 1.25\text{ GHz}$, $\lambda \approx 24.0\text{ cm}$) | NASA / ISRO Payload Specifications |
| **Acquisition Start (UTC)** | **2026-11-10T13:20:27.000Z** | Ingestion Metadata |
| **Acquisition End (UTC)** | **2026-11-10T13:21:00.999Z** ($\Delta t = 33.999\text{ s}$) | Ingestion Metadata |
| **Flight Direction** | **`DESCENDING`** | Orbital State Vectors |
| **Relative Orbit / Track** | **077** | NASA Flight Dynamics Facility |
| **Frame Number** | **084** | Standard NISAR 12-day repeat tiling grid |
| **Orbit Number** | **6750** | Orbit Calculation Domain |
| **Polarization Mode** | **`DHDH`** (Dual Polarisation: Transmit H, Receive H & V) | Product Code `4005` |
| **Granule File Size** | **20,173.65 MB (20.17 GB / 19.70 GiB)** | Exact UMM `granule_size` float |
| **Product Format** | **Hierarchical Data Format 5 (HDF5 / `.h5`)** | NASA SDS Specification D-102269 |
| **Geographic Polygon** | `10.2153°N, 75.80956°E` $\to$ `8.18859°N, 75.33676°E` $\to$ `7.66982°N, 77.57529°E` $\to$ `9.68844°N, 78.05899°E` | Bounding coordinates covering Kuttanad & Vembanad |
| **Companion Covariance Granule** | `NISAR_L2_PR_GCOV_035_077_D_084_4005_DHDH_A_20261110T132027_20261110T132100_P05036_N_F_J_001` | Geocoded Polarimetric Covariance (`C3622241360-ASF`) |
| **Direct HTTPS URL** | `https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GSLC_V1/.../...h5` | ASF Cloud Datapool |
| **Direct S3 URI** | `s3://sds-n-cumulus-prod-nisar-products/NISAR_L2_GSLC_V1/.../...h5` | AWS `us-west-2` Cumulus Bucket |

### Spatial Coverage Visualization:
```
           75.33°E                                78.06°E
  10.22°N  ┌────────────────────────────────────────┐
           │   [North-West Swath Boundary]          │
           │                                        │
           │         KUTTANAD DELTA (9.35°N, 76.40°E)│
           │         • Core Wetland Study Basin     │
           │         • Track 077 Descending Pass    │
           │                                        │
   7.67°N  └────────────────────────────────────────┘
```
The spatial footprint completely encloses the Kuttanad delta study area (`76.33°E, 9.25°N` to `76.55°E, 9.55°N`).

---

## 3. Provenance Dissection: Operational Satellite vs Pre-Operational SDS Stream

A critical objective of this audit is to prevent conflating **pre-operational test streams** with **operational on-orbit acquisitions**.

The granule identifier decomposes into standardized NASA JPL/ISRO Science Data System (SDS) fields:

$$\underbrace{\text{NISAR}}_{\text{Mission}}\_\underbrace{\text{L2}}_{\text{Level}}\_\underbrace{\text{PR}}_{\text{Type}}\_\underbrace{\text{GSLC}}_{\text{Product}}\_\underbrace{035}_{\text{Cycle}}\_\underbrace{077}_{\text{Track}}\_\underbrace{\text{D}}_{\text{Pass}}\_\underbrace{084}_{\text{Frame}}\_\underbrace{4005}_{\text{Mode}}\_\underbrace{\text{DHDH}}_{\text{Polarization}}\_\underbrace{\text{A}}_{\text{Band}}\_\underbrace{20261110\text{T}132027}_{\text{Start}}\_\underbrace{\dots}_{\text{Stop}}\_\underbrace{\text{P}05036}_{\text{SDS Version}}\_\underbrace{\text{N\_F\_J\_001}}_{\text{Downlink Flags}}$$

### Detailed Field Interpretation:
1. **Product Type `PR`**:
   - `PR` denotes **Provisional / Prototype Data Stream** generated during mission validation and Science Data System readiness phases.
   - Contrast with `VA` (Validated Operational Post-Commissioning Release).
2. **Frequency Band Code `A`**:
   - `A` designates the primary **L-Band SAR** ($1.25\text{ GHz}$) developed by NASA JPL.
   - Code `B` designates the Indian Space Research Organisation (ISRO) **S-Band SAR** ($3.20\text{ GHz}$).
3. **Product Level `L2 GSLC`**:
   - Level-2 Geocoded Single Look Complex. Unlike Sentinel-1 Level-1 GRD (which requires local Range-Doppler terrain correction and DEM orthorectification), NISAR GSLC products are already geocoded to map coordinates and provided in polarimetric radar grids.
4. **Data Scale**:
   - A single NISAR GSLC granule is **$20,173.65\text{ MB}$ ($\approx 20.2\text{ GB}$)**.
   - Ingesting a 3-date time series ($t_0, t_1, s_1$) of NISAR GSLC data requires downloading **$\approx 60.5\text{ GB}$** of HDF5 data, compared to $5.42\text{ GB}$ for Sentinel-1 GRDH.

---

## 4. Authentication Gate & Access Boundary Audit

Direct HTTP probes were conducted against the primary data link of granule `NISAR_L2_PR_GSLC_...001`:

```http
GET /NISAR/NISAR_L2_GSLC_V1/NISAR_L2_PR_GSLC_035_077_D_084_4005_DHDH_A_20261110T132027_20261110T132100_P05036_N_F_J_001/NISAR_L2_PR_GSLC_035_077_D_084_4005_DHDH_A_20261110T132027_20261110T132100_P05036_N_F_J_001.h5 HTTP/1.1
Host: nisar.asf.earthdatacloud.nasa.gov
User-Agent: BHnMISnTRA-NISAR-Audit/1.0

HTTP/1.1 401 Unauthorized
Server: nginx
Date: Sat, 14 Nov 2026 18:19:49 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 27
WWW-Authenticate: Basic realm="Please enter your Earthdata Login credentials. If you do not have a Earthdata Login, create one at https://urs.earthdata.nasa.gov//users/new"
Cache-Control: no-store
Strict-Transport-Security: max-age=31536000

HTTP Basic: Access denied.
```

### Forensic Separation of Access Tiers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        TIER A: OPEN UNRESTRICTED METADATA                              │
│  Endpoints: cmr.earthdata.nasa.gov & api.daac.asf.alaska.edu                           │
│  Status: 100% ACCESSIBLE WITHOUT AUTHENTICATION                                        │
│  Payload: JSON / UMM-JSON metadata, orbits, track numbers, frame boundaries,           │
│           bounding polygons, timestamps, exact file sizes, and HTTPS/S3 URIs           │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        TIER B: AUTHENTICATED DATA PAYLOAD                              │
│  Endpoints: nisar.asf.earthdatacloud.nasa.gov & s3://sds-n-cumulus-prod-nisar-products  │
│  Status: STRICTLY BLOCKED (HTTP 401 Unauthorized / AWS S3 403 Forbidden)               │
│  Requirement: Active NASA Earthdata Login credentials (HTTP Basic / OAuth2 bearer token)│
│               or AWS IAM STS temporary credentials for in-region S3 bucket read         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Diagnostic Finding:
1. **Publicly Accessible**: All granule existence metadata, orbital coordinates, and product characteristics are fully verified through open NASA APIs.
2. **Blocked Without Authentication**: The binary HDF5 payload ($20.17\text{ GB}$) is stored in the NASA Cumulus cloud infrastructure (`sds-n-cumulus-prod-nisar-products`) and requires user authentication.
3. **Zero False Claims**: The BHRAMANASTHRA platform **refuses to fabricate local NISAR data arrays**. In the absence of local Earthdata credentials in the automated runtime, the raw `.h5` file was not transferred to disk.

---

## 5. Non-Negotiable Scientific Guardrails & Compliance Audit

### Checkpoint 1: Never Use Synthetic Observations to Claim NISAR Coverage
- **Audit Verification**:
  - The synthetic numpy arrays constructed in `scratch/run_real_data_smoke_test.py` and `tests/` were explicitly designed to simulate Sentinel-1 C-band Level-1 GRDH data.
  - Zero NISAR parameters (e.g. L-band penetration through flooded vegetation, polarimetric decomposition $H/\alpha$, or complex interferometric coherence) were claimed or computed from synthetic data.
  - Synthetic arrays remain strictly classified as **`Tier 3 - Synthetic Fixture`**.

### Checkpoint 2: Never Assume Products Exist Merely Because an Acquisition Was Planned
- **Audit Verification**:
  - The existence of 135 provisional records over Kuttanad in November 2026 does **not** allow retroactive claims for historical flood monitoring.
  - For the primary Kerala Flood benchmark (August 2018), the query returned zero records. The platform strictly reports that **NISAR coverage does not exist for the 2018 disaster**, preventing erroneous assumptions of coverage based on mission planning documents.

### Checkpoint 3: Pipeline and Manifest Immutability
- **Audit Verification**:
  - Zero lines of code in `src/bhnmisntra_science/` or `tests/` were modified.
  - The Sentinel-1 acquisition manifest in [`research/ACQUISITION_MANIFEST.md`](file:///c:/Users/Diya/OneDrive/Apps/nasa/research/ACQUISITION_MANIFEST.md) remains unmodified.
  - All 94 existing unit/integration tests continue passing with 100% compliance.

---

## 6. Scientific Comparison: Sentinel-1 vs NISAR for Flood Intelligence

| Scientific Dimension | Sentinel-1 C-SAR (Operational Baseline) | NISAR L-SAR (Next-Gen Mission) |
| :--- | :--- | :--- |
| **Radar Band & Frequency** | **C-Band** ($5.405\text{ GHz}$, $\lambda = 5.55\text{ cm}$) | **L-Band** ($1.25\text{ GHz}$, $\lambda = 24.0\text{ cm}$) |
| **Canopy Penetration** | Minimal; backscatter reflects off top-of-canopy / foliage. | **High**; penetrates forest canopy, detecting standing water beneath flooded vegetation via double-bounce. |
| **Historical Coverage (2018)** | **Available** (Exact 12-day repeat series on Track 165). | **None** (Temporal archive starts late 2025). |
| **Current Archive Coverage** | Full global coverage (10-year historical archive). | 135 provisional/beta granules over Kuttanad (2025–2026). |
| **Typical Granule Size** | $\approx 0.9\text{ GB}$ (Level-1 GRDH archive). | **$\approx 20.2\text{ GB}$** (Level-2 GSLC `.h5` file). |
| **Geocoding Requirement** | Requires Range-Doppler Terrain Correction & DEM. | **Native geocoded coordinates** (GSLC / GCOV). |
| **Platform Integration Role** | **Core Operational Engine** for historical verification. | **Forward-Looking Engine** for active and upcoming disaster response. |

---

## 7. Conclusions & Strategic Architectural Next Steps

1. **Definitive Finding for 2018 Flood Intelligence**:
   - Sentinel-1 remains the sole authentic SAR mission capable of providing empirical evidence for the August 2018 Kerala Flood disaster.
   - NISAR has zero data for 2018; claiming NISAR historical coverage would constitute scientific hallucination.
2. **Readiness for Future NISAR Ingestion**:
   - The platform has verified actual NISAR archive granules (`NISAR_L2_PR_GSLC_...`) over the Kuttanad delta.
   - The HDF5 data model, polarimetric mode (`DHDH`), and $20.2\text{ GB}$ file sizes are formally mapped in the system's data dictionary.
3. **NASA Earthdata Credential Requirement**:
   - Downloading authentic NISAR binary payloads requires configuring Earthdata Login credentials (`.netrc` or `EARTHDATA_TOKEN`), identically to Sentinel-1 archive downloads.

---

**Audited by**:  
*Lead Data & Scientific Intelligence Specialist (Member 1)*  
*BHRAMANASTHRA Project — NASA Space Apps Challenge 2026*

