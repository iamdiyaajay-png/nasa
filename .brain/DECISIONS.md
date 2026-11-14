# Project Brain: Architectural Decisions (`.brain/DECISIONS.md`)

## ADR-001: Multi-Agent Harness Architecture
- **Context**: Need a robust, autonomous software engineering swarm powered by Gemini Flash High capable of deep planning, zero-slop UI design, strict zero-trust security, and cross-session persistence.
- **Decision**: Synthesize GStack, Ruflo, Claude Council, Strix, Vercel Guidelines, 21st, Headroom, and Project Brain into a unified 6-stage engineering pipeline.
- **Consequences**: Standardized 4-stage execution loop (Explore -> Plan -> Code -> Commit), mandatory `DESIGN.md`, zero client secrets, and pre-commit interactive security audits.

## ADR-002: Zero-Trust Backend Authentication Enclave
- **Context**: Prevent accidental leakage of database credentials, third-party API keys, or JWT signing secrets into client-side bundles (e.g. Next.js, Vite).
- **Decision**: All authentication logic, session cookie management, and database queries are strictly quarantined in backend routes and middleware. Client applications interact exclusively with backend proxy endpoints.
- **Consequences**: Zero exposed client secrets. Requires all auth and data access flows to have corresponding server-side endpoints.

## ADR-003: 34 Production-Grade Pages & UX Resilience Checklist
- **Context**: Real-world applications frequently fail audits and cause silent user drops due to missing edge-case screens (404, offline, session expired, legal policies).
- **Decision**: Enforce the 34-page checklist (15 Legal, 16 Customer Lifecycle, 10 UX States) across all application designs.
- **Consequences**: High compliance and complete user journey coverage from inception.

## ADR-004: Map-First Geographical Exploration Interface & Pre-Investigation Feasibility Gate
- **Context**: Users without GIS, remote-sensing, or radar technical background need to intuitively explore, search down to village level, and select custom study areas without being overwhelmed or misled by speculative results.
- **Decision**: 
  1. Mandate a map-first geographic exploration interface with multi-scale hierarchical geocoding (country down to small neighborhoods and villages).
  2. Implement 3 explicit selection modalities: Administrative boundaries, Freehand polygon drawing, and Rectangle selection (with Edit, Clear, Confirm controls).
  3. Enforce an automatic Pre-Investigation Feasibility Check evaluating spatial swath coverage, compatible SAR repeat acquisitions ($N \ge 3$), and terrain suitability before offering an investigation.
  4. Enforce Progressive Disclosure: Simple explanations and traffic-light cards by default; advanced radar physics and orbit geometry accessible via optional expanders.
  5. Enforce Anti-Hallucination & Honest Status Invariant: Never imply an area has been investigated or evidence exists prior to actual processing.
- **Consequences**: Codified in PRD v3.1 (`PRD.md`) as Section 12, Functional Requirements `FR-0` & `FR-0b`, and Non-Functional Requirements. Guides Member 2 (Backend API) and Member 3 (Frontend/Map) implementation.

