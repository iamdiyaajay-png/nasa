# BHRAMANASTHRA — Product Requirements Document (v3.1, Competition Edition)
### Radar Evidence & Surface Change Intelligence Platform
**NASA Space Apps Challenge 2026** · **Challenge**: *Dancing with the SARs* · **Team of 4** · **Web Application**

---

> **Pitch line**: *Radar can show that the ground changed. BHRAMANASTHRA checks whether the change keeps the beat, meaning whether it behaves over time the way a real event should, and shows its evidence.*

**Status**: Draft v3.1. Items marked `[VERIFY]` must be checked against the official 2026 challenge brief, rules and data pages before the event starts (Section 19 lists them as a task list). This document makes no claim of guaranteed awards or global novelty.

---

## 1. Challenge Fit (Complete Before Building)

Paste the official challenge statement here and fill the table. A PRD that does not trace to the brief is not finished.

**Official challenge statement**: *[PASTE VERBATIM — VERIFY]*

| Challenge requirement or expected outcome | Where we meet it | Evidence in the demo |
| :--- | :--- | :--- |
| `[Requirement 1 — VERIFY]` | | |
| `[Requirement 2 — VERIFY]` | | |
| `[Requirement 3 — VERIFY]` | | |
| **Use of NASA data** | NISAR first, NASA OPERA products as benchmark (Section 11) | Data badges and ledger |
| **Understandable by non-experts** | Method Explainer, plain-language labels, Progressive Disclosure | First-time-user test (Section 16) |

---

## 2. The Idea in One Page

### Problem
Radar (SAR) imagery can show that the surface looks different between two dates. It cannot, on its own, say what happened, whether the signal is real or an artifact, or whether it behaved as expected afterward. Most tools show a colored overlay and stop. Users are left to trust an unverified change mask.

### Solution
BHRAMANASTHRA is a web app for investigating one type of surface change. For a chosen area it:
1. Shows the detected change between two dates;
2. Tests whether the signal **behaves as a real event of that type should** across later acquisitions (the **Beat Test**);
3. Records every input and step in an inspectable **Evidence Ledger**;
4. Labels each region **Supported**, **Inconclusive** or **Unverified**, with stated reasons;
5. Benchmarks the result honestly against a simple baseline and independent reference data.

### Contribution, Stated Narrowly
No new detection algorithm. An **evidence-first workflow** around standard methods, evaluated honestly, with transparent uncertainty.

### Why This Wins Attention
Everyone else will show a change map. We show a change map **plus the reasons to trust it or not**, in a form a non-expert can follow in four minutes.

---

## 3. Who It Helps and Why It Matters

- **Primary Persona: Asha**, a graduate student with a hypothesis (for example, that a flood extent or a forest-clearing scar appears in radar data). She needs to know which acquisitions were used, whether the signal behaves as expected, what could fool the method, and how to cite the result.
- **Second Persona: Ravi**, a local disaster-response or land-management analyst who must decide whether a radar-flagged area is worth a field check or a formal report. He needs a defensible yes, no or *"not enough evidence"*, not a map he cannot explain to his supervisor.
- **Third Persona: Educators** who want a transparent example of radar remote sensing.

### Impact Statement
*[FILL: one sourced statistic on the cost or frequency of the chosen phenomenon in the study region, e.g. flood or deforestation impact. Cite the source in the app.]* Our contribution is to reduce wasted field checks and unsupported claims by making the evidence visible.

### Locally Relevant Framing
If the chosen case study is in a region the team knows (for example Kerala floods or landslides, or another region with a documented event), use it. Judges respond to teams that understand the place. Local relevance must not override data availability (Section 6 scoring).

### Validation with Real People
Interview at least **two people** (a researcher or student, and a practitioner) in 15 minutes each. Ask: how do you currently decide whether a radar change is real; what would make you trust a map; what would you want in a report.

---

## 4. Scope

- **In scope (MVP)**: One case study; one change method; one baseline; one pre-registered Beat Test; Evidence Ledger; three-state evidence labels; reference-based evaluation (lite); reproducible prepared-data demo; **map-first geographical exploration interface with pre-investigation feasibility assessment**.
- **Out of scope (MVP)**: Global or real-time alerts; multi-hazard coverage; causal explanations; AI-generated narratives presented as findings; accounts; decorative 3D.
- **Product principle**: *A detected change is a starting point for investigation, not a confirmed explanation.*

---

## 5. Goals and Success Criteria

These are our engineering targets, not official judging criteria.

| # | Goal | Measurable proof |
| :--- | :--- | :--- |
| **G1** | Show real change | One valid, identified acquisition pair with a computed change layer from real data |
| **G2** | Run the Beat Test | Pre-registered rule applied to at least 3 later acquisitions, dates listed |
| **G3** | Make evidence traceable | Each result has a ledger entry that regenerates it from stated inputs |
| **G4** | Make uncertainty explicit | Three labels with reasons and a written mapping rule; no invented confidence percentages |
| **G5** | Evaluate honestly | Precision, recall and F1 vs. reference, versus baseline, with limitations |
| **G6** | Be understandable | A first-time user explains the output correctly after one minute |
| **G7** | Demo reliably | Full journey in under 4 minutes, repeatable, nothing fabricated |
| **G8** | Non-expert exploration | Users without GIS knowledge search down to village scale, select custom areas, and receive instant feasibility assessments |

---

## 6. Case Study Selection (Decide by Hour 6)

Score each candidate 0–2 on the criteria below. Pick the highest total. A 0 on criterion 1 or 4 eliminates the candidate. Local relevance breaks ties only.

| Criterion | 2 points | 0 points |
| :--- | :--- | :--- |
| **1. Data access** | Suitable NISAR (or fallback SAR) products downloadable and readable now | Cannot be accessed or read |
| **2. Temporal depth** | At least 4 usable acquisitions in the window | Fewer than 3 |
| **3. Method fit** | Well-established method, explainable in 2 minutes | Needs an unproven research method |
| **4. Reference evidence** | Independent reference exists | None |
| **5. Demo value** | Visually clear, meaningful to a general audience | Subtle, hard to interpret |

### Candidates
1. **Flood or inundation** *(Selected: Kuttanad, Kerala 2018)*: Strong, well-understood backscatter change; reference maps exist (e.g. CWC gauges, Sentinel-2 optical, KSDMA reports). Expected behavior: **receding**.
2. **Forest clearing or land-cover change**: Expected behavior: **sustained**. Good temporal depth; weaker drama.
3. **Landslide or surface disturbance**: High value; geometry and vegetation complicate it; references can be sparse. Expected behavior: **sustained**.
4. **Coastal or river-margin change**: Clear signal; reference quality varies.

---

## 7. Scientific Method

Default proposal: **log-ratio of calibrated backscatter with a fixed-rule threshold**.
1. Read co-registered, calibrated SAR backscatter for a reference date and a comparison date from the same geometry (same orbit direction and track) wherever possible.
2. Apply speckle reduction (multilooking or a documented filter in linear space).
3. Compute the log-ratio (difference in dB):
   $$\Delta \sigma^0_{\text{dB}} = \sigma^0_{\text{comp, dB}} - \sigma^0_{\text{ref, dB}}$$
4. Threshold using a rule fixed in advance (for example a multiple of the scene's robust standard deviation, or Otsu's method). Record the value.
5. Remove isolated pixels below a minimum mapping unit (MMU morphological sieving).
6. Output a binary change mask and the continuous log-ratio layer.

### Scientific Safeguards (Non-Negotiable)
- A difference between observations is **not proof of a specific event**.
- Backscatter changes can come from soil moisture, rain, wind, vegetation phenology, freeze-thaw, acquisition geometry, incidence angle, processing differences, and speckle. The ledger names those relevant to the case.
- The Beat Test checks **consistency with an expected temporal pattern**. It does not confirm cause.
- Thresholds and labels are frozen before evaluation. Tuning on the test set is prohibited.
- Mock or illustrative content is always labeled `"ILLUSTRATIVE — NOT REAL DATA"`.

---

## 8. The Beat Test (Pre-Registered)

The rule and the expected behavior are committed to the repository with a timestamp before evaluation runs. Each phenomenon declares its expected behavior up front.

| Phenomenon | Expected temporal behavior | Test |
| :--- | :--- | :--- |
| **Flood or inundation** | **Receding**: detected area shrinks or stays flat over time, never grows without a new event | Detected area in each later acquisition is evaluated across the 4-state model (`PERSISTENT_STAGNATION`, `RECEDING`, `RE_INUNDATED`, `DRAINED`) |
| **Clearing, construction, landslide scar** | **Sustained**: signal remains in later acquisitions | Region re-detected in at least 2/3 of valid later acquisitions |

- **Inputs**: The initial change mask plus $N$ subsequent acquisitions from the same geometry.
- **Contract Gate**: Minimum $N = 3$ subsequent acquisitions for any result other than `Unverified`.
- **Per-region test**: For each later acquisition, compute the same log-ratio against the reference date, apply the same threshold, and compare with the expected behavior.
- **Edge cases**:
  - A missing or invalid acquisition is **excluded**, never counted as "change vanished" or "change persisted".
  - Mixed orbit geometries are not compared with each other; they are flagged.
  - Excluded dates are listed with reasons in the Evidence Ledger.

---

## 9. Evidence Status: The Mapping Rule

The three labels users see are derived from two checks. The rule is fixed before evaluation.

| Check | Values |
| :--- | :--- |
| **Temporal result (T)**, from Section 8 | Matches expected / Does not match / Insufficient |
| **Confounder flag (C)**, from case checklist | Clear / Flagged |

| Label | Rule | What the user is told |
| :--- | :--- | :--- |
| **Supported** | $T = \text{Matches expected} \land C = \text{Clear}$ | The change behaves as an event of this type should, and no known confounder is flagged. *This is not proof of cause.* |
| **Inconclusive** | $T = \text{Does not match} \lor C = \text{Flagged}$ | The change was detected but its behavior or context leaves doubt. Reasons listed. |
| **Unverified** | $T = \text{Insufficient}$ ($< 3$ valid subsequent acquisitions or geometry mismatch) | Not enough repeat observations to test. *We make no claim.* |

*Hard rule: with fewer than 3 valid later acquisitions, no region can be Supported.*

---

## 10. Evaluation Protocol (Written Before Results)

- **Reference data**: Independently sourced, not derived from the same SAR scenes. Source, date, resolution and known errors documented.
- **Procedure**:
  1. Split study area spatially into tuning and test regions before thresholding.
  2. Resample reference and detections to a common grid; document the method.
  3. Compute confusion counts on the test region (precision, recall, F1, false-positive rate).
  4. Report how often Supported regions agree with the reference compared with Inconclusive regions.
  5. State limitations: date mismatch, resolution mismatch, class imbalance, spatial autocorrelation.
- **Honest-outcome clause**: If the Beat Test does not improve precision, we report where it helps, where it does not, and why. A clean negative result is credible.
- **No metric is shown unless computed from this protocol's actual run.** Until then the panel displays *"Evaluation not yet run"*.

---

## 11. Data Strategy (NASA-First)

| Tier | Source | When used |
| :--- | :--- | :--- |
| **1** | NISAR L-band products for the case study (via NASA Earthdata / ASF DAAC) `[VERIFY]` | Preferred |
| **1b** | NASA OPERA products from Sentinel-1 (e.g. DSWx surface water) as a second baseline `[VERIFY]` | If available for the area |
| **2** | Other real open SAR (e.g. Sentinel-1 via ASF DAAC) or challenge-provided data `[VERIFY rules]` | If Tier 1 is not accessible or sufficient |
| **3** | Prepared outputs computed offline from real data | If live processing is unreliable and rules allow |

---

## 12. Geographical Exploration & Area Selection Interface

> ### Core Principle & Invariant
> **BHRAMANASTHRA must provide a highly intuitive, map-first geographical exploration interface. Users with no GIS, remote-sensing or technical knowledge must be able to search for locations at different geographical scales, including villages and small neighbourhoods, navigate the map and select precise custom areas.**
> 
> **Users must be able to select areas through administrative boundaries where available, freehand polygon drawing and rectangle selection. They must be able to edit, clear and confirm their selections.**
> 
> **After selection, the platform must assess geographical coverage, compatible satellite acquisition availability and scientific feasibility before offering an investigation.**
> 
> **The interface must progressively reveal complexity: simple explanations and clear actions for beginners, with optional scientific metadata and methodology for advanced users.**
> 
> **The system must never imply that an area has been investigated or that evidence exists before the relevant data have actually been processed.**

### 12.1 Multi-Scale Search & Interactive Navigation
- **Geocoding Engine**: Search bar supporting hierarchical global geocoding down to:
  - Country / State / Province
  - District / County / Taluk / Tehsil
  - Municipality / Panchayat / Village
  - Local landmarks, polders (*padasekharams*), or street-level small neighborhoods.
- **Navigation Controls**: Smooth vector map navigation with zoom, pan, pitch controls, locator button ("Fly to my location"), and geographic coordinate readout (WGS 84 latitude/longitude).

### 12.2 Area Selection Modalities
The interface provides three explicit selection modes accessible via intuitive toolbar toggles:
1. **Administrative Boundaries**: Instant selection of standardized administrative levels (country, state, district, sub-district/taluk, or village) from vector tile overlays where boundary data is available.
2. **Rectangle Selection (Bounding Box)**: Click-and-drag or corner-point specification for rapid rectangular AOI delimitation.
3. **Freehand & Custom Polygon Drawing**: Point-by-point polygon vertex placement or continuous freehand sketch mode for following natural features (river basins, shorelines, agricultural field clusters).
- **Selection Lifecycle Controls**:
  - **`Edit`**: Drag vertices, translate geometry, or adjust boundary handles.
  - **`Clear`**: Reset active selection and restore full exploration mode.
  - **`Confirm Area`**: Locks geometry, calculates geodesic area, and initiates the Pre-Investigation Feasibility Check.

### 12.3 Pre-Investigation Feasibility & Data Availability Assessment
Upon selection confirmation, before prompting the user to start an investigation or displaying any change layer, the system automatically runs an immediate **Feasibility Assessment**:
1. **Spatial Coverage Check**:
   - Computes overlap against authoritative SAR mission orbital tracks (Sentinel-1 / NISAR swaths).
   - Identifies whether the AOI falls entirely within a single swath or requires along-track / cross-track slice mosaicking.
2. **Temporal Acquisition Availability**:
   - Queries archive catalogs (ASF DAAC / NASA Earthdata) for compatible repeated observations on the same relative orbit and pass direction.
   - Evaluates whether the temporal sequence satisfies the **Beat Test Invariant** ($N \ge 3$ subsequent passes after the event date).
3. **Scientific Feasibility Gate**:
   - Assesses terrain slope (SRTM/Copernicus DEM) to identify layover, shadow, or steep foreshortening risks.
   - Assesses baseline land cover (permanent water, urban density, dense tree canopy).
   - Generates an instant **Feasibility Card**:
     - Status: `FEASIBLE`, `CONDITIONALLY FEASIBLE`, or `UNFEASIBLE`.
     - Estimated observable area, acquisition count, repeat interval, and potential confounders.
     - Only allows launching the investigation if feasibility is established.

### 12.4 Progressive Disclosure Architecture
- **Beginner Mode (Default)**:
  - Plain-language guidance: *"Search for a place or draw a box around the area you want to examine."*
  - Clean visual indicators (Green = Ready, Yellow = Caution/Limited Data, Grey = No Data).
  - One-click action: `"Check Satellite Coverage & Investigate"`.
- **Advanced Scientific Toggle (Optional)**:
  - Full geodetic parameters (WGS 84 ellipsoidal area, UTM projection parameters, bounding coordinates).
  - Orbit details: Relative Orbit number, pass direction (`ASCENDING`/`DESCENDING`), central incidence angle ($\theta$), beam mode (`IW`/`SM`), and polarization (`VV+VH`).
  - Raw JSON metadata view and API payload preview.

### 12.5 The Anti-Hallucination & Honest Status Invariant
- **Strict Prohibition**: The system must **never** display speculative change masks, mock evidence labels, or pre-rendered synthetic overlays on newly selected custom areas without real data processing.
- **Explicit Labeling**: If pre-computed data is displayed for demo purposes, it must be permanently tagged with `"PREPARED BENCHMARK DATA"`. If synthetic fixtures are used, they must be badged `"SYNTHETIC FIXTURE — NOT REAL SATELLITE OBSERVATIONS"`.
- **Zero Evidence Presumption**: An unanalyzed area carries the neutral label `"AWAITING PROCESSING — NO EVIDENCE ASSESSED"`.

---

## 13. Functional Requirements

| ID | Requirement | Description | Priority |
| :--- | :--- | :--- | :---: |
| **FR-0** | **Geographical Exploration & Area Picker** | Map-first search (village to country scale), navigation, 3 selection modes (admin boundaries, freehand polygon, rectangle), edit/clear/confirm controls. Progressive disclosure. | **P0** |
| **FR-0b**| **Pre-Investigation Feasibility Check** | Instant assessment of spatial swath coverage, compatible SAR repeat acquisitions ($N \ge 3$), and terrain suitability before offering investigation. | **P0** |
| **FR-1** | **Change Observatory** | Map, study areas, selectable dates, before / after / change toggle, source, dates and layer explanation. Missing data gives an informative error, never a fake result. | **P0** |
| **FR-2** | **Beat Timeline** | Applies Section 8; shows every acquisition as valid, excluded or detected across the 4-state model; lists dates and reasons; animates region status as dates advance. | **P0** |
| **FR-3** | **Evidence Status Map** | Three-state overlay (Supported, Inconclusive, Unverified) per Section 9 with per-region reasons on click and a legend explaining criteria. | **P0** |
| **FR-4** | **Evidence Ledger** | Schema in Section 14; viewable; downloadable as JSON and a one-page printable report; includes a Reproduce command. | **P0** |
| **FR-5** | **Data Provenance Badges** | Each layer shows `REAL` / `PREPARED` (precomputed from real data) / `ILLUSTRATIVE`, plus the data tier. Anti-hallucination invariant strictly enforced. | **P0** |
| **FR-6** | **Baseline vs Workflow Panel** | Side-by-side output and metrics from Section 10; must be able to show no improvement. | **P1** |
| **FR-7** | **Plain-Language Explainer** | Under 150 words per step, each with its known failure modes and progressive disclosure toggle. | **P1** |
| **FR-8** | **NASA Product Comparison** | Overlay of an official NASA product (e.g. OPERA DSWx) versus ours, with a disclosed agreement summary. | **P1** |
| **FR-9** | **Share and Cite** | Permalink and citation block with data credits and DOI references. | **P2** |

---

## 14. Evidence Ledger Schema

```json
{
  "investigation_id": "INV-2026-0001",
  "study_area": {
    "name": "Kuttanad Agricultural Delta",
    "selection_mode": "RECTANGLE|FREEHAND_POLYGON|ADMIN_BOUNDARY",
    "bbox": [76.3300, 9.2500, 76.5500, 9.5500],
    "geodesic_area_km2": 796.41,
    "crs": "EPSG:4326"
  },
  "phenomenon": {
    "type": "flood",
    "expected_behavior": "receding"
  },
  "data_tier": 1,
  "data_sources": [
    {
      "product_id": "S1A_IW_GRDH_1SDV_20180821T004109_20180821T004134_023337_0289D5_B2B2",
      "mission": "Sentinel-1A",
      "acquisition_utc": "2018-08-21T00:41:09Z",
      "orbit_direction": "DESCENDING",
      "track": 165,
      "url_or_doi": "https://datapool.asf.alaska.edu/GRD_HD/SA/..."
    }
  ],
  "reference_date": "2018-07-28T00:41:08Z",
  "comparison_date": "2018-08-21T00:41:09Z",
  "later_dates": [
    "2018-09-02T00:41:10Z",
    "2018-09-14T00:41:10Z",
    "2018-09-26T00:41:11Z",
    "2018-10-08T00:41:11Z"
  ],
  "method": {
    "name": "log-ratio",
    "version": "git:981a186",
    "parameters": {
      "speckle": "boxcar",
      "window_size": 5,
      "threshold_db": -4.20,
      "min_mapping_unit_pixels": 10
    }
  },
  "signal": {
    "changed_area_km2": 142.85,
    "layer_ref": "layers/diff_log_ratio.tif"
  },
  "beat_test": {
    "temporal_result": "matches",
    "valid_observations": 4,
    "excluded_observations": [],
    "state_transitions": [
      {"date": "2018-09-02", "state": "PERSISTENT_STAGNATION", "area_km2": 140.10},
      {"date": "2018-09-14", "state": "RECEDING", "area_km2": 82.40},
      {"date": "2018-09-26", "state": "RECEDING", "area_km2": 21.15},
      {"date": "2018-10-08", "state": "DRAINED", "area_km2": 2.10}
    ]
  },
  "confounders": {
    "flag": "clear",
    "items": [
      {"name": "wind_roughening", "status": "clear", "value": "2.4 m/s (ERA5)"},
      {"name": "permanent_water", "status": "clear", "value": "JRC mask applied"}
    ]
  },
  "status": {
    "label": "supported",
    "reasons": [
      "Beat Test: Multi-temporal trajectory complies with expected physical profile.",
      "All critical confounders assessed and verified CLEAR. Physical geometry verified."
    ]
  },
  "verification": {
    "reference_source": "CWC Malakkara Gauge (EL 9.58m) & Sentinel-2A Tile T43PFL (26-Sep)",
    "independent_evidence": true,
    "agreement_summary": "F1=0.88 against cloud-free optical validation"
  },
  "limitations": [
    "Sub-canopy flooded vegetation exhibits double-bounce rather than backscatter drop.",
    "CWC Malakkara represents upstream river discharge, not direct polder water depth."
  ],
  "reproduce": {
    "command": "python -m bhnmisntra_science.cli --reproduce INV-2026-0001",
    "config_hash": "a1b2c3d4e5f6",
    "environment": "python-3.11-geospatial"
  }
}
```

---

## 15. Non-Functional Requirements

| Area | Requirement |
| :--- | :--- |
| **Scientific Integrity** | Every result traces to source data and a versioned method. The system never implies an area has been investigated or evidence exists prior to execution. |
| **Reliability** | Failed requests, missing data, and incompatible geometries produce clear messages with next steps; one error format: `{code, message, suggested_action}`. |
| **Performance** | Prepared area loads core view in under 3 seconds; live feasibility check completes in under 2 seconds. Live raster processing is never required for the demo path. |
| **Usability & Simplicity** | A first-time user completes the main journey without instructions. Multi-scale search finds villages in under 1 second. |
| **Progressive Disclosure** | Explanations start at under 100 words with plain-language summaries; technical radar parameters, covariance matrices, and sensor logs are tucked behind an optional expander. |
| **Responsiveness** | Core screens work seamlessly across desktop, laptop, tablet, and mobile viewports. |
| **Transparency** | Dates, sensor sources, limitations, and label criteria are never more than one click away. |
| **Accessibility** | Colorblind-safe palette plus icons/patterns (never color alone); text alternatives for map results; keyboard-navigable controls. |

---

## 16. UX Principles, Screens and Progressive Disclosure

### UX Principles
- **Evidence before verdict**: Say what we do not know (Inconclusive and Unverified carry equal visual weight to Supported).
- **Map-first exploration**: The map is the primary workspace, not a secondary graphic.
- **Progressive complexity**: Beginners see simple spatial drawings and intuitive traffic-light feasibility cards; scientists can open full orbital and incidence angle geometry panels.
- **One investigation, one flow**: No disjointed menus or confusing multi-tab sprawl.

### Flow
`Search / Select Area` $\to$ `Assess Feasibility` $\to$ `Choose Dates` $\to$ `See Change` $\to$ `Run Beat Test` $\to$ `Inspect Ledger` $\to$ `Review Reference Validation`.

### Screens (Keep to Five for the MVP)
1. **Screen 1: Area Explorer & Feasibility Picker**
   - Search bar (villages, districts, coordinates).
   - Selection toolbar: Admin Boundary, Freehand Polygon, Rectangle.
   - Edit, Clear, Confirm buttons.
   - Pre-Investigation Feasibility Card (Coverage, Orbit repeat count, Feasibility status).
2. **Screen 2: Change Observatory with Beat Timeline**
   - Before / After / Difference layer toggle.
   - Interactive timeline scrubber showing acquisitions across time.
3. **Screen 3: Evidence Status Map**
   - Three-state overlay (Supported, Inconclusive, Unverified) with region click popover.
4. **Screen 4: Evidence Ledger & Benchmark Tabs**
   - Complete inspectable ledger, JSON viewer, printable report, baseline comparison.
5. **Screen 5: Method & Scientific Limitations**
   - Plain-language explainer with optional advanced radar physics expander.

---

## 17. Technical Architecture

- **Frontend**: React, MapLibre GL (or Leaflet), Radix UI / Tailwind CSS, timeline component, ledger view; Cloud-Optimized GeoTIFF (COG) or pre-rendered vector/raster tiles.
- **Backend**: FastAPI serving investigations, layers, geocoding endpoints, and ledgers; static serving of prepared outputs.
- **Pipeline**: Python with rasterio, xarray, numpy, scipy, geopandas, shapely. Built as a standalone CLI first, then wrapped by the API.
- **Metadata Store**: Flat JSON or SQLite keyed by investigation ID; zero accounts or authentication friction for judges.
- **Frozen API Endpoints (Hours 1–6)**:
  - `GET /api/geosearch?q={query}` (Hierarchical location search)
  - `POST /api/feasibility-check` (Accepts GeoJSON polygon; returns coverage, track, and pass count)
  - `GET /api/study-areas`
  - `GET /api/study-areas/{id}/acquisitions`
  - `POST /api/investigations`
  - `GET /api/investigations/{id}`
  - `GET /api/investigations/{id}/layers/{layer}`
  - `GET /api/investigations/{id}/evaluation`

---

## 18. Team, Plan and Scope Control

| Member | Owns | Key Deliverables | Backup |
| :--- | :--- | :--- | :--- |
| **1: Data & Science** | Data access, preprocessing, slice mosaicking, change method, Beat Test | CLI that outputs layers, mask, labels, and evidence ledger | Member 4 |
| **2: Backend & Integration** | API, feasibility endpoint, ledger generation, deployment | Frozen API, feasibility evaluator, ledger JSON | Member 1 |
| **3: Frontend & Mapping** | Map-first explorer, selection tools, Beat Timeline, status overlay | Full user journey on prepared & custom data | Member 2 |
| **4: Validation & UX** | Reference data, evaluation, user interviews, demo script, pitch | Metrics, limitations, demo video, submission copy | Member 3 |

---

## 19. Risks and Mitigations

| Risk | Likelihood | Mitigation |
| :--- | :--- | :--- |
| **User selects area with no SAR passes** | High | Pre-investigation feasibility check flags insufficient temporal depth immediately; guides user to verified demo areas. |
| **Non-expert overwhelmed by radar terms** | High | Progressive disclosure: default view uses simple words ("Water appeared and drained over 4 weeks"); radar physics hidden behind "View Scientific Details". |
| **User assumes unanalyzed area has evidence** | Medium | System explicitly states *"Awaiting Processing — No Evidence Assessed"*; never displays colored overlays without processing. |
| **NISAR data hard to access** | High | Sensor-agnostic pipeline; Sentinel-1 Tier 2 fallback verified and fully documented. |
| **Too few repeat acquisitions** | Medium | Hard contract gate: $N < 3$ forces `Unverified`; ledger discloses why. |
| **Environmental confounders (wind/rain)** | High | ERA5 wind speed check ($< 5\text{ m/s}$) and JRC permanent water baseline masking. |

---

## 20. Demo Script (4 Minutes)

| Time | Scene | What we say and show |
| :--- | :--- | :--- |
| **0:00–0:30** | **The Hook & Problem** | Persona story (Asha/Ravi): *"Radar can show that the ground changed. But how do you know it's real and not a sensor artifact?"* |
| **0:30–1:00** | **Map-First Exploration** | Search for a village or draw a custom box; show the instant Feasibility Check verifying satellite coverage and repeat passes. |
| **1:00–1:40** | **Detection** | Toggle Before, After, and Log-Ratio change layer; explain threshold in one sentence. |
| **1:40–2:30** | **Beat Timeline (Wow Moment)**| Step through sequential dates (+12d, +24d, +36d); watch polders transition through stagnation, recession, and drainage; regions dynamically turn `Supported`. |
| **2:30–3:00** | **The Evidence Ledger** | Open the ledger entry; highlight provenance badges; show exact Reproduce command; download JSON. |
| **3:00–3:40** | **Honest Validation** | Show independent CWC gauge hydrograph and Sentinel-2 optical overlay; disclose flooded vegetation limitation. |
| **3:40–4:00** | **Close & Roadmap** | Summarize what the evidence proves; quote user interview; roadmap in one line. |

---

## 21. Pitch Kit and Submission Checklist

- **One-line pitch**: *Radar shows change; BHRAMANASTHRA checks whether the change keeps the beat and shows the evidence.*
- **30-second pitch**: *Problem (colored overlay people must blindly trust) $\to$ what we built (Map-First Explorer, Beat Test, Evidence Ledger, three-state labels) $\to$ what we proved (verified against in-situ river gauges and optical data on real NASA/ESA satellites) $\to$ who it helps (Asha and Ravi).*

---

## Appendix: What Changed in This Version (v3.1)

1. **Map-First Exploration Interface**: Added explicit requirements for multi-scale search (from country down to villages and small neighborhoods) and intuitive map navigation for non-GIS users.
2. **Three Area Selection Modalities**: Mandated administrative boundary selection, freehand polygon drawing, and rectangle selection, complete with Edit, Clear, and Confirm actions.
3. **Pre-Investigation Feasibility Check**: Instituted an automatic pre-flight check of swath coverage, repeat pass availability ($N \ge 3$), and terrain suitability before offering an investigation.
4. **Progressive Disclosure Architecture**: Codified simple explanations and traffic-light cards for beginners, with optional deep radar metadata for advanced users.
5. **Anti-Hallucination & Honest Status Invariant**: Strictly prohibited implying that an area has been investigated or that evidence exists before data is actually processed.
6. **Case Study Specifics**: Formally integrated the audited Kuttanad 2018 flood case study, Relative Orbit 165 Descending geometry, and 4-state recession model.

---
*End of Product Requirements Document (v3.1)*

