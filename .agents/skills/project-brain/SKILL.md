---
name: project-brain
description: Persistent cross-session project memory via .brain/ (MAP.md, STATUS.md, HANDOFF.md, DECISIONS.md).
---

# Project Brain: Cross-Session Persistent Memory Architecture

*(Adapted from ethan-ys/project-brain for Gemini 3.7 / 3.8 Flash High)*

Project Brain provides a standardized persistent memory structure inside the `.brain/` directory at the project root, enabling continuous context retention across restarts, subagents, and development sessions.

## Directory Structure

```text
.brain/
├── MAP.md          # Complete architectural blueprint, directory layout, and subsystem graph
├── STATUS.md       # Real-time task board, active sprints, completed features, known blockers
├── HANDOFF.md      # Context handoff across sessions/subagents, immediate next actions
└── DECISIONS.md    # Architectural Decision Records (ADRs), rationale, rejected alternatives
```

## Specification of Core Files

### 1. `MAP.md` (System Architecture & Subsystem Graph)
- **High-Level Purpose**: The 30,000-foot view of the project.
- **Repository Topology**: File tree highlighting core directories, entry points, and build pipelines.
- **Data Flow & Dependencies**: External services, internal microservices, and database models.
- **Auth & Security Boundary**: Exact demarcation of backend auth middleware and proxy endpoints.

### 2. `STATUS.md` (Real-Time Execution State)
- **Active Sprint & Milestones**: What is currently being built.
- **Done Items**: Checklist of verified, tested components.
- **In-Progress Items**: Current focus with assigned subagents or threads.
- **Blockers & Impediments**: Immediate technical hurdles.

### 3. `HANDOFF.md` (Session Transition Protocol)
- **Immediate Next Action**: Exactly ONE high-priority action for the resuming agent.
- **Context Resume Instructions**: Commands to boot the local environment, test scripts, and relevant file paths.
- **Recent Discoveries**: Gotchas or environmental specifics learned during the last session.

### 4. `DECISIONS.md` (Architectural Decision Records)
- Format:
  - `ADR-001: [Title]`
  - **Context**: Problem statement and constraints.
  - **Decision**: Selected architecture/library/pattern.
  - **Alternatives Considered**: Why competing approaches were rejected.
  - **Consequences**: Long-term trade-offs and maintenance obligations.

## Cross-Project Analysis Routine
When instructed to analyze previous or upcoming projects:
1. Traverse the repository or workspace looking for existing `.brain/` folders or README files.
2. Extract established patterns, design systems, and successful architectural decisions.
3. Ingest reusable modules and security best practices into the current project memory.

