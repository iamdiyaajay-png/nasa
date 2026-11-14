---
name: claude-image-generation
description: High-fidelity prompt synthesizer for UI mockups, vector blueprints, and domain assets.
---

# High-Fidelity Image Generation Synthesizer

This skill synthesizes structured, publication-grade image prompts for technical diagrams, UI wireframes, vector blueprints, and domain-specific assets.

## Prompt Synthesis Grammar

When generating image prompts for UI mockups, architectures, or diagrams, apply the following 5-part structure:

1. **Subject & Domain Context**: Clear focal object (e.g. "Isometric 3D architectural diagram of a distributed telemetry pipeline").
2. **Composition & Spatial Framing**: Perspective, isometric angle, orthographic view, macro crop, or clean grid alignment.
3. **Lighting & Atmosphere**: Soft ambient occlusion, diffuse studio lighting, sharp technical shadows, edge rim lighting.
4. **Color Palette & Materiality**: Matte white surfaces, anodized aluminum accents, translucent frosted glass (glassmorphism), accent neon trails matching the `DESIGN.md` color palette.
5. **Stylistic Constraints & Anti-Negative Words**: "Clean vector blueprint, sharp lines, zero chromatic aberration, zero blurry artifacts, minimalist technical illustration, 8k resolution render".

## Workflows
- Formulate the synthesized prompt.
- Delegate generation to the `image-generator` subagent or direct tool.
- Verify visual output against project design tokens.

