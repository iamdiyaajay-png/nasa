---
name: one-skill-to-rule-them-all
description: Task Observer meta-skill monitoring sessions, capturing user corrections, and refining heuristics automatically.
---

# One Skill to Rule Them All: Task Observer & Adaptive Memory

*(Adapted from rebelytics/one-skill-to-rule-them-all)*

This skill acts as a background observer across development sessions, capturing explicit user corrections, negative feedback, implicit preferences, and edge-case handling to continuously improve agent performance.

## Observer Responsibilities

### 1. Correction Capture & Pattern Detection
- Actively watch for user corrections in chat (e.g., "Don't use X, always use Y", "I told you never to put secrets in frontend", "Prefer arrow functions", "Use pnpm not npm").
- Identify recurring patterns in how the user formats requests, tests code, or expects UI outputs.

### 2. Heuristic Refinement & Rule Generation
- When a consistent preference or correction is identified:
  - Formulate a clean, actionable rule.
  - Record the decision in `.brain/DECISIONS.md`.
  - Propose updating or directly append to workspace rules (`GEMINI.md` or `.agents/rules/user-preferences.md`).

### 3. Skill Self-Healing
- If an agent skill or command fails due to environment differences (e.g. Windows PowerShell syntax vs Bash, sandbox restrictions), update the corresponding skill documentation or scratch helper to prevent repeating the error.

