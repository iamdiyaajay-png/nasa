---
name: claude-prompt-meta-harness
description: Rapid execution modifier triggers from the Claude Prompt Cheat Sheet (SCAFFOLD, REDTEAM, PREMORTEM, DIFF, NO YAP, etc.).
---

# Claude Prompt Meta-Harness: The 25 Rapid Modifiers

When the user includes any of the following triggers or keywords in their prompt, instantly adjust execution mode accordingly:

## The Common Modifiers

| Trigger | Prompt Usage | Execution Behavior |
| :--- | :--- | :--- |
| **`SCAFFOLD`** | `scaffold this first` | Outputs project directory tree, data models, and API interface contracts before writing code. |
| **`PERSONA`** | `you are a [role]` | Adopts an authoritative senior specialist role with deep domain rigor and precision. |
| **`GHOST`** | `/ghost` | Strips all conversational filler, pleasantries, preambles, and robotic AI tone. |
| **`REDTEAM`** | `/redteam` | Adversarially attacks the proposed architecture to uncover failure points, race conditions, and vulnerabilities. |
| **`PREMORTEM`** | `/premortem` | Assumes the project failed catastrophically post-launch; diagnoses root causes today. |
| **`STEP BACK`** | `step back` | Reframes confusing or overly complex tasks from first principles and high-level objectives. |
| **`RANK`** | `rank these` | Prioritizes features, tasks, or bugs by business impact vs. implementation effort (e.g. ICE / RICE scoring). |
| **`RACI`** | `make this a RACI` | Generates a RACI matrix (Responsible, Accountable, Consulted, Informed) for team execution. |
| **`SOP`** | `turn into an SOP` | Converts workflows into a repeatable, step-by-step Standard Operating Procedure. |
| **`NEXT ACTION`** | `next action?` | Delivers exactly ONE single immediate high-priority task, not a list of ten. |
| **`ONE-PAGER`** | `one-pager` | Produces an executive 1-page summary tailored for leadership or jury panels. |
| **`TL;DR`** | `tl;dr` | Delivers the bottom-line actionable conclusion first before providing supporting details. |
| **`DIFF`** | `diff this` | Formats all code modifications strictly as unified git diffs. |
| **`CONSTRAINTS`**| `given ₹X, Y days` | Enforces strict real-world budget, timeline, memory, and compute limits. |
| **`VS`** | `X vs Y` | Direct side-by-side comparison forcing a decisive engineering trade-off selection. |
| **`TIGHTEN`** | `tighten this` | Cuts fluff and condenses copy/code into concise, high-impact bullet points. |
| **`DEVIL'S ADVOCATE`** | `devil's advocate` | Pressure-tests prevailing assumptions with aggressive counter-evidence and alternative hypotheses. |

## Specialized & Analytical Modifiers

| Trigger | Prompt Usage | Execution Behavior |
| :--- | :--- | :--- |
| **`CLIENT VOICE`**| `read as the client` | Reviews the proposal strictly from the client/sponsor perspective. |
| **`ELI5`** | `eli5` | Explains complex technical mechanisms using simple, intuitive real-world analogies. |
| **`SKEPTIC`** | `/skeptic` | Interrogates the underlying premise of the question before answering. |
| **`NO YAP`** | `/noyap` or `no yap` | Skips all conversational talk; outputs direct code, diffs, or commands immediately. |
| **`5 WHYS`** | `5 whys` | Drills down five successive levels to uncover the true root cause of a defect or system failure. |
| **`FLIP IT`** | `flip it` | Inverts the problem and approaches the solution from the inverse angle. |
| **`PROVE IT`** | `prove it` | Backs all claims with empirical numbers, benchmarks, citations, and reproducible evidence. |
| **`WORST CASE`** | `worst case?` | Performs a rapid worst-case scenario risk gut-check and recovery runbook. |

