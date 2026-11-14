# BHRAMANASTHRA: Beat Test Feasibility Assessment
## Case Study: Kuttanad Flood Inundation & Recession (Kerala Floods 2018)

**Platform**: BHRAMANASTHRA — Radar Evidence & Surface Change Intelligence  
**Objective**: Evaluate whether multi-temporal SAR backscatter changes over Kuttanad behave consistently with flood inundation and subsequent hydrological recession over time.

---

### 1. The Pre-Registered Temporal Beat Test Architecture

The central paradigm of BHRAMANASTHRA is that **a single SAR observation is insufficient to establish verified flood evidence**. Surface changes in SAR imagery can arise from temporary soil moisture increases, agricultural tillage, vegetation phenology, or transient standing water.

The **Beat Test** is a pre-registered multi-temporal physical verification protocol:
1. **Initial Detection ($t_0 \to t_1$)**: Log-ratio differencing identifies candidate change clusters:
   $$\Delta \sigma^0_{\text{dB}} = \sigma^0(t_1)_{\text{dB}} - \sigma^0(t_0)_{\text{dB}} \le T_{\text{drop}}$$
2. **Subsequent Trajectory Monitoring ($t_2, t_3, \dots, t_N$)**: Tracks the spatial footprint and detected water area $A(t_k)$ across at least three compatible subsequent observations ($N \ge 3$).
3. **Behavioral Invariant Enforcement**:
   - For a flood event (`expected_behavior = RECEDING`), the detected inundated area within the candidate clusters must exhibit a monotonic downward trend over time:
     $$A(t_k) \le A(t_{k-1}) \times (1 + \text{tolerance})$$
   - Where $\text{tolerance} = 0.05$ (5% measurement noise cushion).
   - If an area completely dries ($A = 0.0\text{ km}^2$), any sudden re-emergence of water ($A > 0.0\text{ km}^2$) without meteorological explanation triggers `UNEXPLAINED_GROWTH` and fails the recession invariant.

---

### 2. Time-Series Construction for Kuttanad

All acquisitions are verified on **Sentinel-1A Relative Orbit 165 (Descending Pass)**:

```
[t0: 28-JUL-2018] ──> [t1: 21-AUG-2018] ──> [t2: 02-SEP-2018] ──> [t3: 14-SEP-2018] ──> [t4: 26-SEP-2018]
  Pre-Flood Ref          Peak Flood           Subsequent 1          Subsequent 2          Subsequent 3
   Baseline dB           Comparison         Early Recession       Mid Recession         Late Drainage
                           (Event)             (+12 days)            (+24 days)            (+36 days)
```

#### 2.1 Geometric Compatibility Verification
- **Satellite Platform**: Sentinel-1A (Identical satellite throughout).
- **Beam Mode**: Interferometric Wide Swath (`IW`) (Identical bandwidth and look angle range).
- **Flight Direction**: `DESCENDING` (Identical azimuth trajectory $\approx 192^\circ$).
- **Relative Orbit**: `165` (Identical cross-track repeat within standard $\pm 100\text{ m}$ orbital tube).
- **Polarization**: `VV + VH` (VV utilized for specular water contrast).
- **Center Incidence Angle**: $\approx 38.5^\circ$ over Kuttanad across all passes ($\Delta \theta < 0.1^\circ$, well within the configured $2.0^\circ$ tolerance).
- **Geometric Uncertainty Flag**: `has_geometry_uncertainty = False`.

#### 2.2 Temporal Cadence & Hydrological Suitability
- **Cadence**: Exactly **12 days** between successive acquisitions.
- **Suitability for Kuttanad**:
  - $t_0 \to t_1$ (24 days): Encompasses the extreme rain spell (14–17 Aug) and dam gate discharges, capturing peak inundation on 21 August.
  - $t_1 \to t_2$ (12 days): Captures initial gravity drainage through the Thottappally spillway and Kochi barmouth.
  - $t_2 \to t_3$ (12 days): Captures active mechanical de-watering of agricultural polders ("padasekharams").
  - $t_3 \to t_4$ (12 days): Captures late-stage drainage, soil re-exposure, and preparation for the subsequent agricultural season.

---

### 3. Hydrological Confounder Analysis & Mitigation

Kuttanad presents unique physical and anthropogenic confounders that must be accounted for to prevent false evidence classification:

| Confounder | Physical Mechanism | Impact on SAR Backscatter | Platform Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Permanent Water Bodies** | Vembanad Lake, major rivers (Pamba, Manimala), and primary navigation canals are permanently inundated. | Permanently low backscatter ($\sigma^0 \approx -20\text{ dB}$) in both $t_0$ and $t_1$. | **JRC Global Surface Water Mask**: Permanent water pixels (occurrence $> 80\%$) are masked out upfront so that only *newly inundated* dry land is evaluated. |
| **Below-Sea-Level Polder Breaches** | Over 60 agricultural polders have dykes below sea level ($-0.5\text{ to } -3.0\text{ m}$). Once breached, water cannot drain by gravity. | Water remains stagnant for 2 to 4 weeks, decaying much slower than upland riverine floods. | **Pre-Registered Recession Slope**: Do not enforce instantaneous 48-hour drainage. Tolerance allows slow, staged recession reflecting mechanical pump capacities ($5\text{--}10\text{ cm/day}$). |
| **Wind-Induced Bragg Roughening** | High surface winds ($> 8\text{ m/s}$) during monsoon squalls create capillary waves matching the C-band radar wavelength ($\sim 5.6\text{ cm}$). | Water surface backscatter increases sharply ($-18\text{ dB} \to -10\text{ dB}$), masquerading as dry land. | **ERA5 Wind Reanalysis Confounder Check**: Overpass wind speed at 00:41 UTC is assessed. If wind $> 6\text{ m/s}$, the acquisition is flagged. (On 21 Aug 00:41 UTC, regional wind over Kuttanad was gentle: $2.4\text{ m/s}$, ideal for calm specular reflection). |
| **Tidal Locking at Outlets** | Semidiurnal ocean tides in the Arabian Sea reverse the hydraulic gradient at the Thottappally spillway and Kochi barmouth twice daily. | High tide causes temporary backwater stagnation or minor upstream water level surges. | **Sequence-Level Trend Analysis**: Evaluate net multi-week recession rather than single-hour fluctuations. |
| **Paddy Emergence / Double-Bounce** | Re-seeded paddy rice emerging from shallow standing water creates dihedral (water-stem) double-bounce reflections. | Backscatter increases sharply ($-18\text{ dB} \to -8\text{ dB}$), signaling vegetative recovery. | Validates transition from flood inundation to post-disaster agricultural recovery. |

---

### 4. Evidence Classification Rules for the Case Study

The final evidence classification will be assigned strictly according to the approved scientific contract:

```
                                  ┌───────────────────────────────┐
                                  │   Beat Test Evaluated (N>=3)  │
                                  └───────────────┬───────────────┘
                                                  │
                         ┌────────────────────────┴────────────────────────┐
                         │                                                 │
                   Beat Test PASSED                                  Beat Test FAILED
             (Area decreases monotonically)                    (Unexplained growth surge)
                         │                                                 │
                         ▼                                                 ▼
          ┌─────────────────────────────┐                            INCONCLUSIVE
          │ Are All Critical Confounders│
          │   Assessed and Verified?    │
          └──────────────┬──────────────┘
                         │
             ┌───────────┴───────────┐
             │                       │
          YES (Clear)             NO (Flagged/Uncertain)
             │                       │
             ▼                       ▼
         SUPPORTED              INCONCLUSIVE
```

- **`SUPPORTED`**:
  - $N_{\text{valid}} \ge 3$ subsequent acquisitions.
  - Orbit 165 geometry verified (identical track, descending, $\Delta \theta < 2.0^\circ$).
  - Beat Test compliant (monotonic floodwater recession across $t_2, t_3, t_4$).
  - Critical confounders (JRC permanent water baseline, ERA5 wind roughening) verified `CLEAR`.
- **`INCONCLUSIVE`**:
  - Sudden unexplained inundation surge during recession without registered rainfall.
  - Critical confounder flagged (e.g. high wind creating ambiguous backscatter).
  - Polder breach unresolved.
- **`UNVERIFIED`**:
  - Fewer than 3 subsequent acquisitions available.
  - Spatial alignment failure or missing geometry metadata.

