# BHRAMANASTHRA: Satellite Acquisition Manifest
## Case Study: Kuttanad Flood Inundation & Recession (Kerala Floods 2018)

**Target Study Polygon**: Core Kuttanad Delta ($76.33^\circ\text{E}$ to $76.55^\circ\text{E}$, $9.25^\circ\text{N}$ to $9.55^\circ\text{N}$)  
**Authoritative Catalogue Sources**: NASA Alaska Satellite Facility (ASF) DAAC / Copernicus Data Space Ecosystem (CDSE)  
**Retrieval Timestamp**: November 2026 (Live API Query)  

---

### 1. Verified Sentinel-1A Compatible Time Series (Relative Orbit 165 — Descending)

This primary time-series meets all geometric compatibility requirements for the pre-registered Beat Test:
- **Satellite**: Sentinel-1A
- **Sensor & Mode**: C-band SAR (5.405 GHz), Interferometric Wide Swath (`IW`)
- **Product Type & Level**: Ground Range Detected High Resolution (`GRDH`), Level-1
- **Polarization**: Dual Polarisation (`VV + VH`)
- **Pass Direction**: `DESCENDING`
- **Relative Orbit / Track**: **165**
- **Nominal Overpass Time**: **00:41 UTC** (06:11 IST)
- **Repeat Period**: Exactly **12.000 days**

| Role in Beat Test | Acquisition Date / Time (UTC) | Exact Product Identifier (`granuleName`) | Path / Orbit | Pass | Spatial Overlap with Polygon | Download Size | Compatibility & Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Reference Baseline ($t_0$)** | 2018-07-28 00:41:08 | `S1A_IW_GRDH_1SDV_20180728T004108_20180728T004132_022987_027EB1_1406` | 165 | DESC | 87.7% (South Frame) / 100% (Mosaicked) | 810.9 MB | **VERIFIED & INCLUDED** (Pre-flood baseline) |
| **Pre-Flood Monitor** | 2018-08-09 00:41:08 | `S1A_IW_GRDH_1SDV_20180809T004108_20180809T004133_023162_02842B_FEE2` | 165 | DESC | 87.8% (South Frame) / 100% (Mosaicked) | 846.8 MB | **VERIFIED & INCLUDED** (Early monsoon inundation) |
| **Event Peak / Comparison ($t_1$)** | 2018-08-21 00:41:09 | `S1A_IW_GRDH_1SDV_20180821T004109_20180821T004134_023337_0289D5_B2B2` | 165 | DESC | 87.7% (South Frame) / 100% (Mosaicked) | 812.4 MB | **VERIFIED & INCLUDED** (Peak flood submergence) |
| **Subsequent 1 ($t_2$)** | 2018-09-02 00:40:45 | `S1A_IW_GRDH_1SDV_20180902T004045_20180902T004110_023512_028F64_618A` | 165 | DESC | 87.7% (North Frame) / 100% (Mosaicked) | 986.0 MB | **VERIFIED & INCLUDED** (Early recession: +12 days) |
| **Subsequent 2 ($t_3$)** | 2018-09-14 00:40:45 | `S1A_IW_GRDH_1SDV_20180914T004045_20180914T004110_023687_029500_F038` | 165 | DESC | 87.7% (North Frame) / 100% (Mosaicked) | 987.9 MB | **VERIFIED & INCLUDED** (Mid recession: +24 days; replaces non-existent 16 Sept) |
| **Subsequent 3 ($t_4$)** | 2018-09-26 00:40:46 | `S1A_IW_GRDH_1SDV_20180926T004046_20180926T004111_023862_029AB0_342E` | 165 | DESC | 87.7% (North Frame) / 100% (Mosaicked) | 996.8 MB | **VERIFIED & INCLUDED** (Late recession / drained: +36 days) |
| **Subsequent 4 ($t_5$)** | 2018-10-08 00:40:46 | `S1A_IW_GRDH_1SDV_20181008T004046_20181008T004111_024037_02A06C_A90F` | 165 | DESC | 87.8% (North Frame) / 100% (Mosaicked) | 1007.9 MB | **VERIFIED & INCLUDED** (Post-flood recovery: +48 days) |
| **Subsequent 5 ($t_6$)** | 2018-10-20 00:40:46 | `S1A_IW_GRDH_1SDV_20181020T004046_20181020T004111_024212_02A61E_2CDE` | 165 | DESC | 87.8% (North Frame) / 100% (Mosaicked) | 1004.0 MB | **VERIFIED & INCLUDED** (Full drainage / agricultural recovery: +60 days) |

---

### 2. Candidate Dates Audit: Literature vs. Satellite Reality

The table below reconciles the candidate dates cited in the published *PLOS ONE* study ([Singha et al., 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7437901/)) against direct NASA ASF DAAC archive records:

| Candidate Date in Paper | Paper Description | Verified in ASF DAAC Archive? | Actual Product ID & Verification Finding | Status in BHRAMANASTHRA |
| :--- | :--- | :--- | :--- | :--- |
| **9 August 2018** | During flood | **YES** | `S1A_IW_GRDH_1SDV_20180809T004108_20180809T004133_023162_02842B_FEE2` | **VERIFIED & VALID** |
| **21 August 2018** | During flood | **YES** | `S1A_IW_GRDH_1SDV_20180821T004109_20180821T004134_023337_0289D5_B2B2` | **VERIFIED & VALID** |
| **2 September 2018** | After flood | **YES** | `S1A_IW_GRDH_1SDV_20180902T004045_20180902T004110_023512_028F64_618A` | **VERIFIED & VALID** |
| **16 September 2018** | After flood | **NO — AUDIT DEFECT** | **ZERO passes exist on 16 September 2018**. The actual Sentinel-1A orbital repeat occurred on **14 September 2018 at 00:40:45 UTC** (`...20180914T004045...`). The published date "16 September" is a clerical/typographical error in the literature. | **REPLACED WITH VERIFIED PASS (14-SEP-2018)** |
| **26 September 2018** | After flood | **YES** | `S1A_IW_GRDH_1SDV_20180926T004046_20180926T004111_023862_029AB0_342E` | **VERIFIED & VALID** |

---

### 3. Excluded Acquisitions (Incompatible Geometry or Pass Direction)

The following candidate acquisitions were retrieved by spatial intersection queries but are **strictly excluded** from the Beat Test sequence:

| Acquisition Date / Time (UTC) | Product Identifier | Track / Orbit | Pass Direction | Reason for Exclusion |
| :--- | :--- | :--- | :--- | :--- |
| **2018-08-21 13:06:02** | `S1A_IW_GRDH_1SDV_20180821T130602_20180821T130631_023345_028A0A_C728` | 173 | **ASCENDING** | **GEOMETRY MISMATCH**: Ascending pass acquires from West-South-West looking East-North-East, creating completely different radar shadow, layover, and local incidence angles compared to Descending Track 165. Mixing ascending and descending passes violates the Beat Test invariant. |
| **2018-08-27 00:40:00** | `S1B_IW_GRDH_1SDV_20180827T004000_20180827T004029_012441_016F10_1CA2` | 165 | DESCENDING | **SENSOR MISMATCH (Sentinel-1B)**: While Sentinel-1B shares the orbit, inter-sensor radiometric calibration cross-biases and differing along-track framing between S1A and S1B can introduce non-physical dB step-offsets. Excluded to maintain a pure, homogeneous Sentinel-1A time-series. |
| **2018-08-27 13:05:33** | `S1B_IW_GRDH_1SDV_20180827T130533_20180827T130558_012449_016F4C_A9FF` | 173 | **ASCENDING** | **DUAL MISMATCH**: Both sensor mismatch (S1B) and pass direction mismatch (Ascending Track 173). |

---

### 4. Along-Track Slice Frame Mosaicking Analysis

The Kuttanad study polygon ($9.25^\circ\text{N}$ to $9.55^\circ\text{N}$) sits directly on the boundary between two successive along-track frames:
- **Frame 1 (North)**: Nominal bounds $[9.23^\circ\text{N}, 11.19^\circ\text{N}]$, $[75.60^\circ\text{E}, 78.20^\circ\text{E}]$.
- **Frame 2 (South)**: Nominal bounds $[7.74^\circ\text{N}, 9.68^\circ\text{N}]$, $[75.32^\circ\text{E}, 77.89^\circ\text{E}]$.

**Empirical Overlap Metrics**:
- Individual Frame 1 covers **$12.2\%$** of Kuttanad during July–August and **$87.7\%$** during September–October (due to ESA orbit frame readjustment).
- Individual Frame 2 covers **$87.8\%$** during July–August and **$12.3\%$** during September–October.
- **Mosaicking Frame 1 + Frame 2 along Track 165 yields $100.0\%$ spatial coverage on every single observation date.**

**Recommended Implementation Strategy**:
Ingest both along-track slices (acquired within 25 seconds of each other in the same orbit pass) and mosaic them prior to spatial clipping to guarantee 100% spatial completeness over Kuttanad.

