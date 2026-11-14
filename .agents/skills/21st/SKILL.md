---
name: 21st
description: Registry for modern React, Tailwind CSS, and Radix UI components (cards, KPI widgets, Cmd+K command bars, telemetry dashboards).
---

# 21st Component Engineering Skill

Inspired by `21st.dev`, this skill governs the selection, composition, and implementation of modern React, Tailwind CSS, and Radix UI components.

## Core Component Standards

1. **Primitive-First Architecture**
   - Build upon unstyled, accessible primitives (@radix-ui/react-dialog, @radix-ui/react-dropdown-menu, @radix-ui/react-tooltip, @radix-ui/react-tabs, @radix-ui/react-popover).
   - Ensure complete keyboard navigation (Tab, Arrow keys, Enter, Escape) and full ARIA compliance out of the box.

2. **Tailwind CSS Architectural Rigor**
   - Leverage `tailwind-merge` and `clsx` via standard `cn()` utility for robust class composition.
   - Use CSS variables for all color tokens (`bg-background`, `text-foreground`, `border-border`, `ring-ring`).
   - Support seamless light and dark mode switching with system preference detection (`dark:` variants).

3. **High-Frequency Production Components**
   - **Command Palettes (`Cmd+K`)**: Rapid search, keyboard-navigable action lists, fuzzy matching, and category groupings.
   - **Interactive KPI & Telemetry Cards**: Metric value, delta indicator (+/- percentage with color tint), mini sparkline chart, and drill-down trigger.
   - **Data Tables**: Paginated, sortable columns, multi-filter dropdowns, bulk actions, and responsive horizontal scroll.
   - **Form Steppers & Wizards**: Multi-step progressive disclosure with validation at each checkpoint and persistent drafts.
   - **Slide-over Sheets & Drawer Menus**: Smooth gesture/backdrop dismissal with trapped focus.

4. **Integration with Taste & DESIGN.md**
   - All 21st components must strictly adhere to the spatial grid and color tokens defined in the workspace `DESIGN.md`.
   - Never embed hardcoded hex colors or non-standard border-radius values.

