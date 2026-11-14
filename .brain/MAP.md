# Project Brain: Map (`.brain/MAP.md`)

## Project Information
- **Project Name**: NASA Mission Workspace
- **Workspace Path**: `c:\Users\Diya\OneDrive\Apps\nasa`
- **Architecture Harness**: Antigravity Pro Multi-Agent Swarm (GStack + Ruflo + Claude Council + Strix + Vercel Guidelines + 21st + Headroom + Project Brain)
- **Primary Reasoning Model**: Gemini Flash High

## Repository Topology & Structure
```text
nasa/
├── .agents/
│   ├── rules/
│   └── skills/
│       ├── 21st/                       # Radix UI + Tailwind component registry
│       ├── awesome-design-md/          # DESIGN.md protocol generator
│       ├── claude-code-setup/          # Explore -> Plan -> Code -> Commit loop
│       ├── claude-image-generation/    # Technical prompt synthesizer
│       ├── claude-prompt-meta-harness/ # 25 rapid cheat sheet prompt modifiers
│       ├── headroom/                   # 60-90% token compression proxy
│       ├── one-skill-to-rule-them-all/ # Task Observer & adaptive memory
│       ├── playwright-cli/             # E2E multi-viewport testing & audits
│       ├── project-brain/              # Persistent cross-session memory
│       ├── strix-pentest/              # Interactive pentest & backend auth enclave
│       ├── swarm-council/              # GStack + Ruflo + Claude Council deliberation
│       ├── taste-skill/                # Anti-slop UI & 34 production pages
│       └── web-design-guidelines/      # Vercel UI & WCAG 2.1 AA/AAA audit
├── .brain/
│   ├── MAP.md                          # Repository map & architectural blueprint
│   ├── STATUS.md                       # Real-time task board & milestones
│   ├── HANDOFF.md                      # Cross-session state & next actions
│   └── DECISIONS.md                    # Architectural Decision Records (ADRs)
├── src/
│   └── bhnmisntra_science/             # Member 1 Data & Scientific Intelligence module
│       ├── constants.py                # Mathematical and PRD frozen constants
│       ├── enums.py                    # Scientific domain enums
│       ├── exceptions.py               # Domain typed exceptions
│       ├── types.py                    # Strict input validation & UTC handlers
│       ├── config.py                   # Pydantic v2 metadata & parameter schemas
│       ├── policies.py                 # Incidence angle, confounder, & classifier policies
│       ├── pipeline.py                 # End-to-end scientific pipeline orchestrator
│       ├── processing/                 # SAR signal processing (calibration, alignment, speckle, log-ratio, mosaicking)
│       └── beat_test/                  # Multi-temporal trajectory & re-inundation tracking
├── tests/
│   ├── conftest.py                     # Synthetic test fixtures (Tier 3)
│   ├── run_tests.py                    # Unittest discovery runner
│   ├── test_stage1_contracts.py        # 31 contract & schema invariants tests
│   ├── test_processing.py              # 22 signal processing & Beat Test tests
│   ├── test_slice_assembler.py         # 17 direct abutting slice assembly tests
│   ├── test_four_state_tracker.py      # 13 four-state temporal Beat Test tracking tests
│   ├── test_pipeline_integration.py    # 8 Phase 2.3 pipeline integration tests
│   └── test_pipeline_e2e.py            # 3 full-stack end-to-end pipeline tests
├── research/                           # Authoritative scientific audit & specification records
│   ├── PHASE_1_1_INDEPENDENT_AUDIT.md
│   ├── PHASE_1_2_DATA_GATE_AUDIT.md
│   ├── PHASE_1_3_IMPLEMENTATION_READINESS.md
│   ├── PHASE_1_4_SCIENTIFIC_RULE_VALIDATION.md
│   ├── PHASE_1_4_1_CORRECTION_AUDIT.md
│   ├── PHASE_1_5_SCIENTIFIC_SPECIFICATION.md
│   ├── PHASE_2_1_SLICE_ASSEMBLER_REPORT.md
│   ├── PHASE_2_2_TEMPORAL_TRACKER_REPORT.md
│   ├── PHASE_2_2_1_INDEPENDENT_AUDIT.md
│   ├── PHASE_2_3_PIPELINE_INTEGRATION_REPORT.md
│   ├── PHASE_2_4_REAL_DATA_SMOKE_TEST.md
│   ├── PHASE_2_4_1_EVIDENCE_PROVENANCE_AUDIT.md
│   └── PHASE_2_5_NISAR_ARCHIVE_AND_COVERAGE_AUDIT.md
├── BHnMISnTRA_PRD.pdf                  # Historical PRD specification (v3)
├── PRD.md                              # Authoritative Master PRD specification (v3.1)
├── GEMINI.md                           # Master bootstrap prompt & execution rules
├── .gitignore                          # Exclusion rules
└── README.md                           # Comprehensive documentation & test metrics
```

## Security & Auth Enclave Demarcation
- **Frontend Layer**: Zero client-side keys or database access. All secrets filtered from client bundles.
- **Backend API & Middleware**: Strictly encapsulates JWT verification, session cookies, database access, and external API calls.

