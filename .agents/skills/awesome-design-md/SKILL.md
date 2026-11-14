---
name: awesome-design-md
description: DESIGN.md protocol generator for enforcing spatial rules, color tokens, and font scales.
---

# Awesome DESIGN.md Protocol

This skill enforces the creation, maintenance, and adherence to a canonical `DESIGN.md` file in the project root.

## Protocol Lifecycle

1. **Initialization Phase**
   - When scaffolding a new application or major frontend module, generate `DESIGN.md` in the project root before writing UI code.
   - The file acts as the single source of truth for all styling, typography, spacing, and component states.

2. **Required Specification Sections**

   ### 1. Color Palette Tokens
   - CSS variable definitions for semantic roles:
     - `--background` & `--foreground`
     - `--card` & `--card-foreground`
     - `--primary` & `--primary-foreground`
     - `--secondary` & `--secondary-foreground`
     - `--muted` & `--muted-foreground`
     - `--accent` & `--accent-foreground`
     - `--destructive` & `--destructive-foreground`
     - `--border`, `--input`, `--ring`
   - Contrast validation: verify minimum 4.5:1 ratio for text and 3:1 for interactive controls.

   ### 2. Typography Hierarchy
   - Font family definitions (Primary sans, display serif/grotesk, code mono).
   - Fluid type scale:
     - `text-xs`: 12px / line-height 16px
     - `text-sm`: 14px / line-height 20px
     - `text-base`: 16px / line-height 24px
     - `text-lg`: 18px / line-height 28px
     - `text-xl`: 20px / line-height 28px
     - `text-2xl`: 24px / line-height 32px
     - `text-3xl`: 30px / line-height 36px
     - `text-4xl`: 36px / line-height 40px

   ### 3. Spatial Rules & Grid
   - 8pt grid system for section layout (`p-4`, `p-6`, `p-8`, `gap-6`, `gap-8`).
   - 4pt micro-grid for input paddings, chip badges, and icon margins (`p-1`, `p-2`, `gap-2`).
   - Standard container widths: `max-w-7xl` for dashboards, `max-w-4xl` for forms/documentation, `max-w-md` for auth modals.

   ### 4. Interactive States
   - Explicit definitions for: default, hover, active, focus-visible (2px outline with offset), disabled (opacity 50%, pointer-events-none), and loading (animated spinner / skeleton).

3. **Enforcement Routine**
   - Every UI component review must cross-check against `DESIGN.md`. Any divergence without explicit architectural approval is rejected.

