---
name: headroom
description: Context compression proxy reducing JSON, log, and RAG tokens by 60–90% for Gemini 3.7 / 3.8 Flash High.
---

# Headroom: Context Compression Protocol

*(Adapted from headroomlabs-ai/headroom for Gemini 3.7 / 3.8 Flash High)*

Headroom enforces strict context discipline to eliminate token bloat, maximize reasoning depth, and keep conversation trajectories fast and responsive.

## Core Compression Techniques (60–90% Token Reduction)

1. **Selective Telemetry & JSON Compaction**
   - **Never dump raw, unformatted multi-megabyte JSON payloads** directly into active chat turns.
   - Use JSON projection: extract only relevant top-level keys or specific records using PowerShell/Python one-liners (`Select-Object`, `jq`, or Python dictionary comprehensions).
   - Convert verbose repeated JSON objects into condensed tabular or Markdown summary formats.

2. **Log Stream Filtering & Head/Tail Sampling**
   - For build logs, server outputs, or test runs exceeding 50 lines:
     - Isolate error lines, stack traces, and failure exit codes.
     - Strip repetitive timestamp prefixes, thread IDs, and informational heartbeats.
     - Sample the first 10 lines (command initialization) and the last 30 lines (failure root cause).

3. **Codebase AST & Range-Bound Reads**
   - Never read entire files exceeding 500 lines when searching for a single function or interface.
   - Use targeted `StartLine` and `EndLine` parameters in `read_file`.
   - Use regex and structural search (`Select-String` / `grep`) before opening files.

4. **Offload Heavy Context to Persistent Artifacts**
   - Offload large summaries, schema dictionaries, and API contract specifications into markdown artifacts in `<appDataDir>\brain\<conversation-id>\` or scratch files in `scratch/`.
   - Maintain a concise high-level pointer in the main conversation context.

