# BHRAMANASTHRA: Reference Evidence Manifest
## Case Study: Kuttanad Flood Inundation & Recession (Kerala Floods 2018)

**Primary SAR Sensor under Test**: Sentinel-1A C-SAR (Track 165 Descending)  
**Verification Principle**: Strict separation between (A) independent ground truth / physical validation and (B) non-independent SAR-derived comparison products.

---

### 1. Independent Reference Datasets (Ground Truth & Non-Sentinel-1 Sources)

| Reference Dataset Name | Source Organization | Acquisition / Publication Date | Sensor / Data Type | Spatial / Temporal Resolution | Geographic Coverage | Independence from Sentinel-1 | Temporal Alignment with SAR Passes | Scientific Utility & Known Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NRSC/ISRO NDEM Flood Inundation Maps** | National Remote Sensing Centre (NRSC), ISRO | August 9, 11, 14, 16, 17, 18, 19, 21, 2018 | Multi-sensor (Radarsat-2 SAR, Resourcesat-2 AWiFS optical) | 25 m – 56 m spatial | All Kerala flood-affected districts including Alappuzha | **HIGHLY INDEPENDENT** (Combines Radarsat-2 and Indian IRS satellites) | Aligns directly with Peak Flood ($t_1 = 2018\text{-}08\text{-}21$) | **Strengths**: Authoritative national emergency flood extent. **Limitations**: Coarser resolution (25–56m) than Sentinel-1 (10m); boundary generalization. |
| **CWC Hydrological Gauge Records** | Central Water Commission (CWC), Govt. of India | Daily / Hourly throughout July – October 2018 | In-situ hydrometric water-level & discharge stations | Point measurements (hourly gauge height in meters above MSL) | Chengannur (Pamba), Neelimangalam (Meenachil), Mankombu (Kuttanad interior) | **100% INDEPENDENT** (Physical in-situ river gauges) | Continuous temporal coverage spanning all $t_0 \to t_6$ SAR passes | **Strengths**: Direct physical ground measurement of water level rise and drainage rate without atmospheric or speckle noise. **Limitations**: Point measurements; spatial interpolation required across polders. |
| **KSDMA Official Flood Memorandum 2** | Kerala State Disaster Management Authority (KSDMA) | Published 13 September 2018 | Official government post-disaster field survey & damage registry | Administrative panchayat / taluk level | Alappuzha, Kuttanad, Chengannur, Ambalappuzha taluks | **100% INDEPENDENT** (Ground civil administration reports) | Captures cumulative impacts across August – September 2018 | **Strengths**: Confirms physical polder wall breaches, 60+ bund breaks, and prolonged waterlogging up to mid-September. **Limitations**: Tabular and administrative; not a pixel-level spatial raster. |
| **Sentinel-2A Cloud-Free Optical Imagery** | European Space Agency (ESA) / Copernicus | **2018-09-27 05:16:51 UTC** | Multispectral Instrument (MSI) — Bands 2, 3, 4, 8, 11 (MNDWI) | 10 m – 20 m spatial | Tile `T43PEJ` (Full Kuttanad & Vembanad Lake coverage) | **INDEPENDENT SENSOR** (Optical / SWIR sensor, distinct physical mechanism) | Exactly 1 day after Subsequent 3 ($t_4 = 2018\text{-}09\text{-}26$) | **Strengths**: High-resolution (10m) cloud-free optical verification of drained polders and standing water; confirms whether SAR backscatter increase represents real surface drying. **Limitations**: Cloud cover prevents optical observations during the peak flood (8–21 August). |

---

### 2. Non-Independent & Processed Comparison Products

These products are derived from Sentinel-1 or share its input data. They are useful for **algorithm cross-checking**, but **MUST NEVER be cited as independent ground truth**:

| Product Name | Source Organization | Sensor / Heritage | Spatial Resolution | Why It Is NON-INDEPENDENT | Role in BHRAMANASTHRA |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **OPERA DSWx-S1** | NASA JPL / PO.DAAC | Derived from Sentinel-1 SAR | 30 m | **Directly derived from Sentinel-1 backscatter**. Sharing the same input data means any systematic radar artifacts (e.g. Bragg scattering from wind-roughened water) will be shared. In addition, historical OPERA DSWx-S1 production began primarily from 2023 onward. | Evaluated only as a benchmark processing pipeline comparison; excluded from ground truth validation. |
| **GEE Published Flood Extents (Singha et al., 2020)** | PLOS ONE ([PMC7437901](https://pmc.ncbi.nlm.nih.gov/articles/PMC7437901/)) | Derived from Sentinel-1 GRD in Google Earth Engine | 10 m | **Utilizes the exact same Sentinel-1 granules** processed via Otsu thresholding in GEE. | Methodological cross-comparison for threshold selection ($T \approx -3.5\text{ to } -4.2\text{ dB}$). |
| **Vanama et al., 2021 Change Index** | European Journal of Remote Sensing ([10.1080/22797254.2020.1867901](https://www.tandfonline.com/doi/full/10.1080/22797254.2020.1867901)) | Multi-temporal Sentinel-1 Normalized Change Index (NCI) | 10 m | **Directly calculated from Sentinel-1 C-SAR backscatter differences**. | Reference for expected backscatter change ranges during Kerala flood recession. |

---

### 3. OPERA DSWx-HLS Cloud Evaluation

The OPERA Dynamic Surface Water Extent from Harmonized Landsat-Sentinel (DSWx-HLS) product was investigated as a candidate optical surface water source:
- **Spatial Resolution**: 30 m.
- **Coverage**: Global land surface.
- **Audit Finding during August 2018 Peak Flood**:
  Between 8 August and 22 August 2018, central Kerala experienced continuous heavy precipitation under the active monsoon trough. Cloud cover exceeded **98%** in all daytime optical passes.
- **Result**: DSWx-HLS quality assessment (QA) flags mark all pixels over Kuttanad as `CLOUD_OR_CLOUD_SHADOW_OBSCURED`. Therefore, DSWx-HLS **cannot** provide optical surface water comparison for the peak flood acquisition ($t_1 = 2018\text{-}08\text{-}21$). It is usable only for the late recession phase ($t_4 = 2018\text{-}09\text{-}26 / 27$).

